"""Pipeline de reponse : recherche -> extraits -> generation JSON -> validation des citations."""

from __future__ import annotations

import copy
import logging
import re
import threading
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as DelaiDepasse

from api import concordance, lexique, prompts
from api.citations import valider_reponse
from api.journal import Journal
from api.llm.base import LLM, LLMError
from api.matieres import sources_par_matiere, sources_pour
from api.references import extraire
from api.retrieval.base import SEUIL_COUVERTURE, Complement, Retriever, groupes
from api.textes import SOURCES_TEXTES, en_vigueur_aujourdhui

AVERTISSEMENT = (
    "Réponse générée par une intelligence artificielle. Lexia est un outil d'étude, pas un avis juridique : "
    "vérifiez toujours les sources citées, en particulier la version en vigueur des textes."
)
K_CHAT = 8
MAX_SUGGESTIONS = 4  # articles ajoutes sans recherche (lexique, concordance, reformulation)
K_SECOURS = 4  # extraits envoyes au modele de secours (quota Groq gratuit : ~8 000 jetons par minute)
log = logging.getLogger("lexia.rag")
# La reformulation (appel Gemini) tourne pendant la vectorisation de la question ; au-dela du delai,
# la recherche part sans elle (le resultat tardif est abandonne).
_REFORMULATIONS = ThreadPoolExecutor(max_workers=20, thread_name_prefix="reformulation")
CACHE_REPONSES = 500           # reponses gardees en memoire (identiques pour une meme question)
CACHE_DUREE_S = 24 * 3600      # l'index ne change qu'a la publication, qui redemarre le service


def cle_question(question: str, *contexte) -> tuple:
    """Question normalisee (casse, espaces, ponctuation finale) + mode, matiere, niveau..."""
    q = re.sub(r"\s+", " ", question.lower()).strip().rstrip(" ?!.")
    return (q, *contexte)


class CacheReponses:
    def __init__(self, maximum: int = CACHE_REPONSES, duree: float = CACHE_DUREE_S):
        self._max, self._duree = maximum, duree
        self._items: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, cle: tuple) -> dict | None:
        with self._lock:
            v = self._items.get(cle)
            if v is None or time.monotonic() - v[0] > self._duree:
                self._items.pop(cle, None)
                return None
            self._items.move_to_end(cle)
            return copy.deepcopy(v[1])

    def mettre(self, cle: tuple, reponse: dict) -> None:
        with self._lock:
            self._items[cle] = (time.monotonic(), copy.deepcopy(reponse))
            self._items.move_to_end(cle)
            while len(self._items) > self._max:
                self._items.popitem(last=False)


def table_extraits(passages: list[dict]) -> dict[str, dict]:
    return {f"S{i}": p for i, p in enumerate(passages, start=1)}


def fiche_source(p: dict, label: str | None = None) -> dict:
    meta = p.get("meta") or {}
    en_vigueur = en_vigueur_aujourdhui(meta, p["source_id"])
    return {
        "id": p["id"],
        "label": label,
        "source_id": p["source_id"],
        "type": p["type"],
        "numero": p.get("numero"),
        "entete": p.get("entete") or p.get("titre"),
        "url": p["url"],
        "version": p.get("version", ""),
        "en_vigueur": en_vigueur,
        # « 2999-01-01 » : date de remplacement de quelques decisions dans les archives DILA, jamais affichee
        "date": None if str(meta.get("date") or "").startswith("2999") else (meta.get("date") or meta.get("date_debut")),
        "extrait": p["texte"][:400] + ("…" if len(p["texte"]) > 400 else ""),
    }


def sources_citees(reponse: dict, table: dict[str, dict]) -> list[dict]:
    """Fiches des passages effectivement cites, dans l'ordre de premiere citation."""
    par_id = {p["id"]: (label, p) for label, p in table.items()}
    ordre: list[str] = []
    for cle in ("droit_positif", "explication", "points_incertains"):
        for it in reponse.get(cle, []):
            for pid in it["sources"]:
                if pid not in ordre:
                    ordre.append(pid)
    return [fiche_source(par_id[pid][1], par_id[pid][0]) for pid in ordre if pid in par_id]


def pour_secours(passages: list[dict], k: int = K_SECOURS) -> list[dict]:
    """Les k extraits envoyes au modele de secours : k - 1 textes (ou cours) et la meilleure decision.

    Les extraits arrivent textes d'abord : en prendre les k premiers privait le secours de toute decision
    (les questions sur une decision du Conseil constitutionnel echouaient toutes, backtest du 2026-11-12).
    """
    juris = [i for i, p in enumerate(passages) if p["source_id"] not in SOURCES_TEXTES and p.get("type") != "cours"]
    autres = [i for i in range(len(passages)) if i not in set(juris)]
    garde = autres[:k - 1] + juris[:1]
    for i in range(len(passages)):
        if len(garde) >= k:
            break
        if i not in garde:
            garde.append(i)
    return [passages[i] for i in sorted(garde)]


class Disjoncteur:
    """Apres `seuil` echecs d'affilee du modele principal, on passe directement au secours pendant `pause` secondes.

    Gemini gratuit renvoie souvent des 503 en serie : sans disjoncteur, chaque question attendait le budget complet
    (35 s) avant le secours. A la fin de la pause, un essai est refait ; s'il echoue, le disjoncteur se rouvre aussitot.
    """

    def __init__(self, seuil: int = 3, pause: float = 300.0, horloge=time.monotonic):
        self.seuil, self.pause, self._horloge = seuil, pause, horloge
        self._echecs, self._jusqua = 0, 0.0
        self._lock = threading.Lock()

    def ouvert(self) -> bool:
        with self._lock:
            return self._horloge() < self._jusqua

    def echec(self) -> None:
        with self._lock:
            essai_apres_pause = self._jusqua > 0
            self._echecs += 1
            if essai_apres_pause or self._echecs >= self.seuil:
                self._jusqua = self._horloge() + self.pause
                log.warning("disjoncteur ouvert : modele de secours seul pendant %.0f s", self.pause)

    def succes(self) -> None:
        with self._lock:
            self._echecs, self._jusqua = 0, 0.0


class Lexia:
    def __init__(self, retriever: Retriever, llm: LLM, journal: Journal | None = None, embedder=None,
                 expanseur=None, reclasseur=None, delai_reformulation: float = 8.0, cache: CacheReponses | None = None,
                 secours: LLM | None = None, disjoncteur: Disjoncteur | None = None):
        self.secours = secours        # None : pas de modele de secours (Groq)
        self.disjoncteur = disjoncteur if disjoncteur is not None else Disjoncteur()
        self.delai_reformulation = delai_reformulation
        self.cache = cache if cache is not None else CacheReponses()
        self.retriever = retriever
        self.llm = llm
        self.journal = journal or Journal(None)
        self.embedder = embedder      # None : recherche lexicale seule
        self.expanseur = expanseur    # None : pas de reformulation de la question
        self.reclasseur = reclasseur  # None : pas de reclassement
        self.cours = None             # api.cours.Cours : cours deposes par les etudiants (avec les comptes)

    def rechercher(self, texte: str, matiere: str | None, k: int) -> tuple[list[dict], dict]:
        """Renvoie les passages et un resume de la recherche (pour le controle et les journaux)."""
        sources = sources_pour(matiere)
        toutes = tuple(sorted({s for ids in sources_par_matiere().values() for s in ids}))
        textes, juris = groupes(sources, toutes)
        vectoriel = self.embedder is not None and any(
            g and self.retriever.couverture(g) >= SEUIL_COUVERTURE for g in (textes, juris))
        refs = extraire(texte)
        anciens = concordance.anciens_numeros(refs)
        # Articles connus sans appel au modele : articles actuels d'un ancien numero cite, puis lexique.
        locales = list(dict.fromkeys([("code_civil", n) for ns in anciens.values() for n in ns]
                                     + lexique.suggestions(texte)))
        # Question qui cite deja un article, une decision ou un pourvoi : la recherche par reference le trouve,
        # la reformulation couterait un appel Gemini (et ses 503) pour peu de gain.
        futur = None
        # Disjoncteur ouvert : Gemini est en panne, la reformulation ferait attendre pour rien.
        en_panne = self.secours is not None and self.disjoncteur.ouvert()
        if self.expanseur is not None and refs.vide and not en_panne:
            futur = _REFORMULATIONS.submit(self.expanseur.etendre, texte)
        vecteur = self.embedder.embed_query(texte) if vectoriel else None
        complement = None
        if futur is not None:
            try:
                complement = futur.result(timeout=self.delai_reformulation)
            except DelaiDepasse:
                futur.cancel()  # encore en file d'attente : n'appellera pas Gemini pour rien
                log.info("reformulation trop lente (> %.0f s) : recherche sans elle", self.delai_reformulation)
        reformule = complement is not None
        if locales:
            complement = complement or Complement()
            complement.suggestions = list(dict.fromkeys(locales + complement.suggestions))[:MAX_SUGGESTIONS]
        if complement and complement.reformulation and vectoriel:
            complement.vecteur_reformulation = self.embedder.embed_query(complement.reformulation)
        hits = self.retriever.search(texte, sources=sources, k=k, query_vector=vecteur,
                                     complement=complement, reclasseur=self.reclasseur)
        # Article d'une matiere speciale (successions...) dont la question ne parle pas : ecarte, sauf s'il est cite.
        hits = [h for h in hits if "reference" in h.via or not lexique.hors_matiere(h.passage, texte)]
        passages = [h.passage for h in hits]
        if anciens and (sources is None or "code_civil" in sources):
            # Texte d'avant la reforme, place juste apres les references citees : le modele peut le comparer.
            rang = sum(1 for h in hits if "reference" in h.via)
            vus = {p["id"] for p in passages}
            for ancien in anciens:
                v = concordance.ancienne_version(self.retriever.versions("code_civil", ancien))
                if v is not None and v["id"] not in vus:
                    passages.insert(rang, v)
                    rang += 1
        infos = {
            "recherche": "hybride" if any("vecteur" in h.via for h in hits) else "lexicale",
            "reformulation": reformule,
            "reclassement": self.reclasseur is not None,
            "suggestions_retenues": sum(1 for h in hits if "suggestion" in h.via),
            "lexique": len(locales),
        }
        if anciens:
            infos["concordance"] = {a: list(ns) for a, ns in anciens.items()}
        return passages, infos

    def extraits(self, texte: str, matiere: str | None, k: int, cours_ids: list[int] | None = None,
                 avec_officiel: bool = True, uid: int | None = None) -> tuple[list[dict], dict]:
        """Passages pour une demande : corpus seul, cours de l'etudiant seul, ou les deux entrelaces.

        Entrelacer garde un melange cours / officiel meme quand le modele de secours n'en recoit que 4.
        """
        if not cours_ids or self.cours is None or uid is None:
            return self.rechercher(texte, matiere, k)
        vecteur = self.embedder.embed_query(texte) if self.embedder is not None else None
        if not avec_officiel:
            du_cours = self.cours.rechercher(uid, cours_ids, texte, k, vecteur)
            return du_cours, {"recherche": "cours", "reformulation": False, "reclassement": False,
                              "suggestions_retenues": 0, "cours": len(du_cours)}
        du_cours = self.cours.rechercher(uid, cours_ids, texte, (k + 1) // 2, vecteur)
        officiels, infos = self.rechercher(texte, matiere, k - len(du_cours))
        melange = [p for paire in zip(du_cours, officiels) for p in paire]
        n = min(len(du_cours), len(officiels))
        melange += du_cours[n:] + officiels[n:]
        return melange, {**infos, "cours": len(du_cours)}

    def generer(self, *, system: str, construire, passages: list[dict], schema: dict,
                temperature: float = 0.2) -> tuple[dict, str, list[dict]]:
        """Modele principal avec tous les extraits ; s'il echoue, modele de secours avec les K_SECOURS premiers.

        construire(passages) -> prompt. Renvoie (JSON brut, modele utilise, passages reellement envoyes) :
        les citations sont ensuite validees contre ces passages-la.
        """
        if self.secours is not None and self.disjoncteur.ouvert():
            erreur_principal = LLMError("disjoncteur ouvert : modele principal en panne recente")
        else:
            try:
                brut, modele = self.llm.generate_json(system=system, prompt=construire(passages), schema=schema,
                                                      temperature=temperature)
                self.disjoncteur.succes()
                return brut, modele, passages
            except LLMError as e:
                if self.secours is None:
                    raise
                self.disjoncteur.echec()
                log.warning("modele principal indisponible (%s) : modele de secours", str(e)[:200])
                erreur_principal = e
        reduits = pour_secours(passages)
        try:
            brut, modele = self.secours.generate_json(system=system, prompt=construire(reduits), schema=schema,
                                                      temperature=temperature)
        except LLMError as e2:
            raise LLMError(f"{erreur_principal}; {e2}") from None
        return brut, modele, reduits

    def chat(self, question: str, mode: str, matiere: str | None, niveau: str | None = None,
             semestre: int | None = None, cours_ids: list[int] | None = None, avec_officiel: bool = True,
             uid: int | None = None) -> dict:
        debut = time.monotonic()
        reponse_id = str(uuid.uuid4())
        avec_cours = bool(cours_ids) and self.cours is not None and uid is not None
        option_cours = ("avec_officiel" if avec_officiel else "seul") if avec_cours else None
        cle = cle_question(question, mode, matiere, niveau, semestre)
        deja = None if avec_cours else self.cache.get(cle)  # cours personnel : jamais de cache partage
        if deja is not None:
            self.journal.ecrire("requetes", route="chat", reponse_id=reponse_id, mode=mode, matiere=matiere,
                                statut=deja["statut"], cache=True, duree_ms=int((time.monotonic() - debut) * 1000))
            deja["controle"]["cache"] = True
            return {**deja, "reponse_id": reponse_id}
        passages, infos = self.extraits(question, matiere, K_CHAT, cours_ids, avec_officiel, uid)
        recherche = infos["recherche"]
        table = table_extraits(passages)
        modele = None
        if not passages and mode not in prompts.MODES_METHODE:
            # Rien trouve : abstention sans appeler le modele. Une demande de methode s'explique sans extrait.
            reponse, controle = valider_reponse({"statut": "abstention"}, table)
        else:
            brut, modele, passages = self.generer(
                system=prompts.SYSTEME,
                construire=lambda ps: prompts.prompt_chat(question, mode, ps, niveau, semestre,
                                                          infos.get("concordance"), option_cours),
                passages=passages,
                schema=prompts.schema_reponse(mode),
            )
            table = table_extraits(passages)
            reponse, controle = valider_reponse(brut, table, mode)
        sources = sources_citees(reponse, table)
        self.journal.ecrire(
            "requetes", route="chat", reponse_id=reponse_id, mode=mode, matiere=matiere,
            statut=reponse["statut"], recherche=recherche, modele=modele,
            passages_fournis=[p["id"] for p in passages], passages_cites=[s["id"] for s in sources],
            controle=controle.as_dict(), recherche_detail=infos, duree_ms=int((time.monotonic() - debut) * 1000),
        )
        res = {
            "reponse_id": reponse_id,
            **reponse,
            "sources": sources,
            "avertissement": AVERTISSEMENT,
            "controle": {**controle.as_dict(), **infos, "passages_consultes": len(passages),
                         "modele_appele": modele is not None},
        }
        if reponse["statut"] == "reponse" and not avec_cours:
            self.cache.mettre(cle, res)
        return res

    # --- verification de vigueur ----------------------------------------------

    def vigueur(self, passage_id: str) -> dict | None:
        p = self.retriever.get(passage_id)
        if p is None:
            return None
        meta = p.get("meta") or {}
        base = {"id": p["id"], "source_id": p["source_id"], "version": p.get("version", ""), "url": p["url"]}
        if p["source_id"] in SOURCES_TEXTES and p["source_id"] != "constitution_1958":
            en_vigueur = bool(en_vigueur_aujourdhui(meta, p["source_id"]))
            actuelle = None
            nouveaux = concordance.REFORME_2016.get(p.get("numero") or "") \
                if p["source_id"] == "code_civil" and meta.get("date_fin") == concordance.DATE_REFORME else None
            if nouveaux:
                # Ancien numero : la version actuelle du meme numero aurait un autre objet.
                for v in self.retriever.versions("code_civil", nouveaux[0]):
                    if en_vigueur_aujourdhui(v.get("meta") or {}, "code_civil"):
                        actuelle = {"id": v["id"], "version": v["version"], "url": v["url"]}
                        break
                art = "à l'article" if len(nouveaux) == 1 else "aux articles"
                return {**base, "applicable": True, "en_vigueur": False, "version_en_vigueur": actuelle,
                        "message": (f"Ancienne numérotation, en vigueur jusqu'au 1er octobre 2016. Son contenu se "
                                    f"retrouve aujourd'hui {art} {', '.join(nouveaux)} du Code civil. "
                                    "Confirmez sur Légifrance avant de vous y fier.")}
            if not en_vigueur:
                texte = meta.get("id_texte")
                for v in self.retriever.versions(p["source_id"], p.get("numero") or ""):
                    vm = v.get("meta") or {}
                    # « article 14 » existe dans des centaines de lois : rester dans le meme texte.
                    if texte and vm.get("id_texte") and vm["id_texte"] != texte:
                        continue
                    if vm.get("en_vigueur"):
                        actuelle = {"id": v["id"], "version": v["version"], "url": v["url"]}
                        break
            message = ("Cette version est en vigueur selon la dernière synchronisation."
                       if en_vigueur else
                       "Cette version n'est plus en vigueur." + (" Une version en vigueur existe." if actuelle else
                                                                " Aucune version en vigueur de cet article n'a été trouvée (abrogé ou transféré)."))
            return {**base, "applicable": True, "en_vigueur": en_vigueur, "version_en_vigueur": actuelle,
                    "message": message + " Confirmez sur Légifrance avant de vous y fier."}
        if p["source_id"] == "constitution_1958":
            return {**base, "applicable": True, "en_vigueur": True, "version_en_vigueur": None,
                    "message": "Texte en vigueur selon la dernière synchronisation. Confirmez sur le site du Conseil constitutionnel."}
        return {**base, "applicable": False, "en_vigueur": None, "version_en_vigueur": None,
                "message": ("Une décision de justice n'a pas de version en vigueur. Vérifiez sa portée actuelle : "
                            "revirement de jurisprudence, réforme des textes appliqués.")}

