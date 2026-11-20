"""Jurisprudence recente hors archives DILA (D113) : API Judilibre (desactivee sans cle) et site du Conseil
constitutionnel. Reponses enregistrees dans tests/fixtures, aucun appel reseau."""

import io
import json
import shutil
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from ingest import build_index, mise_a_jour
from ingest.sources import cass, constit, constit_site, judilibre_api

FIX = Path(__file__).parent / "fixtures"
JUD = FIX / "judilibre"
CC = FIX / "conseil_constitutionnel"


def archive(chemin: Path, fichiers: dict[str, bytes]) -> Path:
    with tarfile.open(chemin, "w:gz") as tar:
        for nom, data in fichiers.items():
            info = tarfile.TarInfo(nom)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return chemin


class Api:
    """Faux serveur : reponses enregistrees par chemin, requetes gardees pour les verifier."""

    def __init__(self, reponses: dict[str, object]):
        self.reponses, self.requetes = reponses, []

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.requetes.append(requete)
        cle = requete.url.path
        if cle == "/cassation/judilibre/v1.0/export":
            cle += f"?batch={requete.url.params['batch']}"
        r = self.reponses.get(cle)
        if r is None:
            return httpx.Response(404)
        return httpx.Response(200, json=r) if isinstance(r, (dict, list)) else httpx.Response(200, text=r)

    def client(self, **kw) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self), **kw)


def lire(nom: str):
    return json.loads((JUD / nom).read_text(encoding="utf-8"))


EXPORT = "/cassation/judilibre/v1.0/export"


def judilibre(api: Api) -> httpx.Client:
    return api.client(base_url=judilibre_api.URL_API, headers={"KeyId": "cle-de-test"})


# --- Judilibre ----------------------------------------------------------------------------

def test_judilibre_premiere_synchronisation(tmp_path):
    api = Api({f"{EXPORT}?batch=0": lire("export_lot0.json"), f"{EXPORT}?batch=1": lire("export_lot1.json")})
    with judilibre(api) as http:
        n = judilibre_api.synchroniser(http, tmp_path, "2026-05-12",
                                       maintenant=datetime(2026, 11, 20, 3, 30, tzinfo=timezone.utc))
    # arret civil et arret social gardes ; arret ancien (avant la fenetre), ordonnance et arret supprime ecartes
    assert sorted(f.stem for f in (tmp_path / "decisions").glob("*.json")) == [
        "6a0000000000000000000001", "6a0000000000000000000002"]
    assert n == {"ecrites": 2, "retirees": 1}
    r = api.requetes[0]
    assert r.headers["KeyId"] == "cle-de-test"
    assert r.url.params.get_list("publication") == ["b", "r"]
    assert (r.url.params["jurisdiction"], r.url.params["type"], r.url.params["date_type"],
            r.url.params["date_start"], r.url.params["batch_size"]) == ("cc", "arret", "creation", "2026-05-12", "1000")
    assert [q.url.params["batch"] for q in api.requetes] == ["0", "1"]
    assert judilibre_api.date_synchro(tmp_path) == "2026-11-20"


def test_judilibre_synchronisations_suivantes_et_suppressions(tmp_path):
    api = Api({f"{EXPORT}?batch=0": lire("export_lot0.json"), f"{EXPORT}?batch=1": lire("export_lot1.json")})
    with judilibre(api) as http:
        judilibre_api.synchroniser(http, tmp_path, "2026-05-12", datetime(2026, 11, 20, tzinfo=timezone.utc))
    api = Api({f"{EXPORT}?batch=0": lire("export_maj.json"),
               "/cassation/judilibre/v1.0/transactionalhistory": lire("transactionalhistory.json")})
    with judilibre(api) as http:
        n = judilibre_api.synchroniser(http, tmp_path, "2026-05-12", datetime(2026, 11, 21, tzinfo=timezone.utc))
    assert n == {"ecrites": 1, "retirees": 1}
    hist, export = api.requetes
    assert hist.url.params["date"] == "2026-11-17"   # 3 jours avant la synchronisation precedente
    assert (export.url.params["date_type"], export.url.params["date_start"]) == ("update", "2026-11-17")
    restants = judilibre_api.decisions(tmp_path)
    assert [d["id"] for d in restants] == ["6a0000000000000000000001"]   # arret social supprime par la Cour
    assert restants[0]["summary"].endswith("(sommaire corrigé)")


def test_judilibre_arret_en_passages_sans_composition_ni_moyens_annexes():
    d = lire("export_lot0.json")["results"][0]
    ps = judilibre_api.parse_decision(d, date_recuperation="r", version="v")
    assert [p.id for p in ps] == ["judilibre:6a0000000000000000000001:sommaire", "judilibre:6a0000000000000000000001:1",
                                  "judilibre:6a0000000000000000000001:2"]
    som, motifs, dispositif = ps
    assert som.alineas[0].startswith("BAIL COMMERCIAL - Conclusion")
    assert motifs.type == "motifs" and motifs.numero == "1-5"
    assert dispositif.type == "dispositif" and dispositif.texte.startswith("PAR CES MOTIFS")
    tout = "\n".join(p.texte for p in ps)
    assert "Teiller" not in tout and "Composition" not in tout   # introduction : pas de noms de magistrats
    assert "MOYEN ANNEXE" not in tout and "Ainsi fait et jugé" not in tout
    assert som.titre == "Cour de cassation, Troisième chambre civile, 19 novembre 2026, 25-17.523, Publié au bulletin"
    assert som.url == "https://www.courdecassation.fr/decision/6a0000000000000000000001"
    assert som.meta["numeros_pourvoi"] == ["25-17523"] and som.meta["date"] == "2026-11-19"
    assert build_index.doc_id(som.to_dict()) == "judilibre:6a0000000000000000000001"


def test_judilibre_sans_zonage_filtre_comme_l_archive():
    d = lire("export_lot1.json")["results"][0]
    ps = judilibre_api.parse_decision(d, date_recuperation="r", version="v")
    assert {p.source_id for p in ps} == {"cass_sociale"}
    tout = "\n".join(p.texte for p in ps)
    assert tout.startswith("Faits et procédure") and "Huglo" not in tout and "MOYEN ANNEXE" not in tout


def test_cass_complete_l_archive_sans_doublon(tmp_path):
    raw = tmp_path / "raw"
    (raw / "dila").mkdir(parents=True)
    archive(raw / "dila" / "Freemium_cass_global_20261108-140000.tar.gz",
            {"cass/JURITEXT000044900853.xml": (FIX / "cass_moderne.xml").read_bytes()})
    cache = raw / "judilibre" / "decisions"
    cache.mkdir(parents=True)
    for d in [lire("export_lot0.json")["results"][0], lire("decision_dans_archive.json")]:
        (cache / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False))
    (raw / "judilibre" / "etat.json").write_text(json.dumps({"synchro": "2026-11-20T03:30:00+00:00"}))
    ps = list(cass.collect(raw / "dila", date_recuperation="r"))
    docs = {p.meta.get("id_dila") or p.meta["id_source"] for p in ps}
    # meme ECLI que l'arret de l'archive : la copie Judilibre est ignoree
    assert docs == {"JURITEXT000044900853", "judilibre:6a0000000000000000000001"}
    recent = [p for p in ps if "id_source" in p.meta]
    assert {p.version for p in recent} == {"Open data de la Cour de cassation (Judilibre), mise à jour du 2026-11-20"}


def test_cass_sans_cache_judilibre_inchange(tmp_path):
    archive(tmp_path / "Freemium_cass_global_20261108-140000.tar.gz",
            {"cass/JURITEXT000044900853.xml": (FIX / "cass_moderne.xml").read_bytes()})
    ps = list(cass.collect(tmp_path, date_recuperation="r"))
    assert ps and all(p.version == "Archive DILA CASS du 2026-11-08" for p in ps)


# --- Site du Conseil constitutionnel ------------------------------------------------------

def test_liste_des_dernieres_decisions():
    l = constit_site.liste((CC / "decisions.html").read_text(encoding="utf-8"))
    assert len(l) == 10
    assert l["/decision/2026/20261233QPC.htm"] == "2026-1233|QPC"
    assert l["/decision/2026/20261230_1231QPC.htm"] == "2026-1230|QPC"
    assert l["/decision/2026/2026340L.htm"] == "2026-340|L"


def test_decision_du_site_en_passages():
    html = (CC / "20261230_1231QPC.htm").read_text(encoding="utf-8")
    ps = constit_site.parse_page(html, date_recuperation="r", version="v", source_id=constit.SOURCE_ID)
    assert [p.type for p in ps] == ["motifs"] * 4 + ["dispositif"]
    assert ps[0].id == "decisions_conseil_constitutionnel:20261230_1231QPC:1" and ps[0].numero == "1-6"
    assert ps[0].alineas[0].startswith("1. Il y a lieu de joindre")
    assert ps[-1].texte.startswith("LE CONSEIL CONSTITUTIONNEL DÉCIDE :")
    m = ps[0].meta
    assert (m["numero"], m["nature"], m["date"], m["ecli"]) == (
        "2026-1230/1231", "QPC", "2026-10-23", "ECLI:FR:CC:2026:2026.1230.QPC")
    assert m["solution"] == "Non conformité totale"
    assert ps[0].entete.startswith("Conseil constitutionnel, décision n° 2026-1230/1231 QPC du 23 octobre 2026 - ")
    assert ps[0].url == "https://www.conseil-constitutionnel.fr/decision/2026/20261230_1231QPC.htm"


def test_page_changee_refusee():
    with pytest.raises(constit_site.ParseError):
        constit_site.lire("<html><body><p>Maintenance</p></body></html>")


def _site() -> Api:
    return Api({"/decisions": (CC / "decisions.html").read_text(encoding="utf-8"),
                "/decision/2026/20261233QPC.htm": (CC / "20261233QPC.htm").read_text(encoding="utf-8"),
                "/decision/2026/20261230_1231QPC.htm": (CC / "20261230_1231QPC.htm").read_text(encoding="utf-8")})


def _deja_sauf(*gardees: str) -> set[str]:
    """Cles des decisions de la liste, sauf celles a telecharger : comme si l'archive DILA avait les autres."""
    return {c for ch, c in constit_site.liste((CC / "decisions.html").read_text(encoding="utf-8")).items()
            if ch not in gardees}


def test_synchronisation_du_site_ne_telecharge_que_le_nouveau(tmp_path):
    site = _site()
    deja = _deja_sauf("/decision/2026/20261233QPC.htm", "/decision/2026/20261230_1231QPC.htm")
    with site.client() as http:
        assert constit_site.synchroniser(http, tmp_path, deja) == ["20261233QPC", "20261230_1231QPC"]
        assert constit_site.synchroniser(http, tmp_path, deja) == []   # deja en cache
    assert [r.url.path for r in site.requetes].count("/decision/2026/20261233QPC.htm") == 1
    # l'archive DILA contient desormais la 2026-1233 : retiree du cache
    with site.client() as http:
        constit_site.synchroniser(http, tmp_path, deja | {"ECLI:FR:CC:2026:2026.1233.QPC"})
    assert sorted(f.name for f in tmp_path.glob("*.htm")) == ["20261230_1231QPC.htm"]


def test_constit_complete_l_archive(tmp_path):
    raw = tmp_path / "raw"
    (raw / "dila").mkdir(parents=True)
    archive(raw / "dila" / "Freemium_constit_global_20261108-140000.tar.gz",
            {"constit/CONSTEXT000049184152.xml": (FIX / "constit_2023-1075_QPC.xml").read_bytes()})
    (raw / constit.RAW_SITE).mkdir()
    for n in ("20261233QPC", "20261230_1231QPC"):
        shutil.copy(CC / f"{n}.htm", raw / constit.RAW_SITE / f"{n}.htm")
    assert "2023-1075|QPC" in constit.cles_dila(raw / "dila")
    ps = list(constit.collect(raw / "dila", date_recuperation="r"))
    dates = {p.meta["numero"]: p.meta["date"] for p in ps}
    assert dates == {"2023-1075": "2024-01-18", "2026-1233": "2026-11-20", "2026-1230/1231": "2026-10-23"}
    assert {p.version.split(",")[0] for p in ps} == {"Archive DILA CONSTIT du 2026-11-08",
                                                       "Site du Conseil constitutionnel"}


# --- Mise a jour nocturne et fraicheur ----------------------------------------------------

def test_mise_a_jour_judilibre_desactive_sans_cle(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mise_a_jour, "ROOT", tmp_path)   # pas de .env lu
    monkeypatch.delenv(judilibre_api.VARIABLE_CLE, raising=False)
    monkeypatch.setattr(constit, "cles_dila", lambda raw: _deja_sauf("/decision/2026/20261233QPC.htm"))
    appele = []
    monkeypatch.setattr(judilibre_api, "synchroniser", lambda *a, **k: appele.append(a))
    (tmp_path / "dila").mkdir()
    site = _site()
    with site.client() as http:
        assert mise_a_jour.jurisprudence_recente(tmp_path / "dila", http) == []
    assert appele == [] and all(r.url.host == "" or "piste" not in r.url.host for r in site.requetes)
    assert "Judilibre : desactive (JUDILIBRE_KEY_ID absente)" in capsys.readouterr().out
    assert [f.name for f in (tmp_path / constit.RAW_SITE).glob("*.htm")] == ["20261233QPC.htm"]


def test_mise_a_jour_judilibre_avec_cle_et_echec_sans_blocage(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mise_a_jour, "ROOT", tmp_path)
    monkeypatch.setenv(judilibre_api.VARIABLE_CLE, "cle-de-test")
    monkeypatch.setattr(constit, "cles_dila", lambda raw: set())
    raw = tmp_path / "dila"
    archive(raw.mkdir() or raw / "Freemium_cass_global_20261108-140000.tar.gz", {})
    vus = []
    monkeypatch.setattr(judilibre_api, "synchroniser",
                        lambda http, dossier, debut: vus.append((http.headers["KeyId"], dossier, debut))
                        or {"ecrites": 0, "retirees": 0})
    alertes = []
    monkeypatch.setattr(mise_a_jour.fraicheur, "alerter", lambda m, sujet=None: alertes.append(m) or 0)
    with Api({}).client() as http:   # site du Conseil en panne (404)
        echecs = mise_a_jour.jurisprudence_recente(raw, http)
    assert vus == [("cle-de-test", tmp_path / "judilibre", "2026-05-12")]   # 180 jours avant la globale CASS
    assert len(echecs) == 1 and echecs[0].startswith("site du Conseil constitutionnel")
    assert alertes and "jurisprudence recente" in alertes[0]


def test_site_du_conseil_desactivable_par_l_editeur(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mise_a_jour, "ROOT", tmp_path)
    monkeypatch.delenv(judilibre_api.VARIABLE_CLE, raising=False)
    monkeypatch.setenv(constit_site.VARIABLE_ARRET, "0")
    (tmp_path / constit.RAW_SITE).mkdir()
    shutil.copy(CC / "20261233QPC.htm", tmp_path / constit.RAW_SITE)
    site = _site()
    with site.client() as http:
        assert mise_a_jour.jurisprudence_recente(tmp_path / "dila", http) == []
    assert site.requetes == [] and not (tmp_path / constit.RAW_SITE).exists()
    assert "desactive (LEXIA_SITE_CONSEIL_CONSTITUTIONNEL=0)" in capsys.readouterr().out


def test_decisions_recentes_dans_la_signature_des_archives(tmp_path):
    raw = tmp_path / "dila"
    raw.mkdir()
    for f in mise_a_jour.FONDS:
        archive(raw / f"Freemium_{f}_global_20261108-140000.tar.gz", {})
    avant = mise_a_jour.archives_lues(raw)
    (tmp_path / constit.RAW_SITE).mkdir()
    shutil.copy(CC / "20261233QPC.htm", tmp_path / constit.RAW_SITE)
    apres = mise_a_jour.archives_lues(raw)
    assert apres[:-1] == avant and apres[-1].startswith("CONSEIL_CONSTITUTIONNEL_1_")
    (tmp_path / constit.RAW_SITE / "20261233QPC.htm").write_text("modifiee")
    assert mise_a_jour.archives_lues(raw)[-1] != apres[-1]


def test_origine_de_la_decision_la_plus_recente(tmp_path):
    from api.retrieval.local import LocalRetriever

    (tmp_path / "passages").mkdir()
    dila_ps = cass.parse_arret((FIX / "cass_moderne.xml").read_bytes(), date_recuperation="r",
                               version="Archive DILA CASS du 2026-11-08")
    recents = judilibre_api.parse_decision(lire("export_lot0.json")["results"][0], date_recuperation="r",
                                           version="Open data de la Cour de cassation (Judilibre), mise à jour du 2026-11-20")
    (tmp_path / "passages" / "judilibre.jsonl").write_text(
        "\n".join(json.dumps(p.to_dict(), ensure_ascii=False) for p in [*dila_ps, *recents]))
    build_index.build(passages_dir=tmp_path / "passages", index_dir=tmp_path / "index", cache_dir=tmp_path / "vide",
                      model="aucun")
    con = sqlite3.connect(tmp_path / "index" / "lexia.sqlite")
    assert con.execute("SELECT date, origine FROM fraicheur").fetchall() == [
        ("2026-11-19", "Open data de la Cour de cassation (Judilibre), mise à jour du 2026-11-20")]
    con.close()
    r = LocalRetriever(tmp_path / "index")
    assert r.origines_decisions() == {"judilibre": "Open data de la Cour de cassation (Judilibre), mise à jour du 2026-11-20"}
