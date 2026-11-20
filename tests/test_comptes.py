"""Comptes, sessions, formules et quotas."""

import pytest
from fastapi.testclient import TestClient

from api.admin import main as admin
from api.comptes import Comptes, ErreurCompte, hacher_mdp, verifier_mdp
from api.config import Settings
from api.llm.base import LLMError
from api.main import create_app
from api.retrieval.base import Hit

PASSAGE = {"id": "code_civil:A1240", "source_id": "code_civil", "type": "article", "numero": "1240",
           "entete": "Code civil, article 1240", "texte": "Tout fait quelconque de l'homme...",
           "url": "https://exemple", "version": "v", "meta": {"en_vigueur": True}}
REPONSE = {"statut": "reponse", "titre": "t", "droit_positif": [{"texte": "Règle.", "sources": ["S1"]}],
           "explication": [], "points_incertains": [], "message": ""}


class Retriever:
    mode = "test"

    def search(self, question, **kw):
        return [Hit(PASSAGE, 1.0, {"lexical"})]

    def get(self, pid):
        return PASSAGE if pid == PASSAGE["id"] else None

    def versions(self, s, n):
        return [PASSAGE]

    def couverture(self, s):
        return 0.0

    def stats(self):
        return {"moteur": "test", "passages": 1, "embeddings": 0}


class LLM:
    def __init__(self):
        self.echec = False

    def generate_json(self, **kw):
        if self.echec:
            raise LLMError("503")
        return REPONSE, "fake"


@pytest.fixture
def env(tmp_path):
    comptes = Comptes(tmp_path / "comptes.db")
    llm = LLM()
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=llm, comptes=comptes)
    return TestClient(app), comptes, llm


def inscrire(client, email="etu@exemple.fr", mdp="motdepasse-solide"):
    return client.post("/auth/inscription", json={"email": email, "mot_de_passe": mdp, "accepte_cgu": True,
                                                  "prenom": "Léa", "nom": "Martin"})


def test_mot_de_passe_hache():
    h = hacher_mdp("motdepasse-solide")
    assert h.startswith("scrypt$") and "motdepasse" not in h
    assert verifier_mdp("motdepasse-solide", h) and not verifier_mdp("autre", h)


def test_inscription_connexion_deconnexion(env):
    client, _, _ = env
    assert client.get("/auth/session").json() is None
    r = inscrire(client)
    assert client.get("/auth/session").json()["email"] == "etu@exemple.fr"
    assert r.status_code == 201 and r.json()["formule"]["id"] == "gratuit"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/auth/moi").json()["email"] == "etu@exemple.fr"
    assert client.post("/auth/deconnexion").status_code == 204
    assert client.get("/auth/moi").status_code == 401
    r = client.post("/auth/connexion", json={"email": "ETU@exemple.fr ", "mot_de_passe": "motdepasse-solide"})
    assert r.status_code == 200
    assert client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "faux"}).status_code == 401


def test_inscription_refusee(env):
    client, _, _ = env
    assert client.post("/auth/inscription", json={"email": "a@b.fr", "mot_de_passe": "motdepasse-solide",
                                                  "accepte_cgu": False}).status_code == 422
    assert inscrire(client, email="pas-un-email").status_code == 422
    assert inscrire(client, mdp="court").status_code == 422
    inscrire(client)
    assert "existe déjà" in inscrire(client).json()["detail"]


def test_plafond_d_inscriptions_par_ip(tmp_path):
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              inscriptions_par_ip_jour=3),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    assert inscrire(client, email="pris@exemple.fr").status_code == 201
    # Un refus compte aussi : « un compte existe deja » permettait de tester des adresses sans limite.
    assert inscrire(client, email="pris@exemple.fr").status_code == 422
    assert inscrire(client, email="b@exemple.fr").status_code == 201
    r = inscrire(client, email="c@exemple.fr")
    assert r.status_code == 429 and "demain" in r.json()["detail"]


def test_origine_etrangere_refusee(env):
    client, _, _ = env
    r = client.post("/auth/inscription", headers={"Origin": "https://pirate.exemple"},
                    json={"email": "x@y.fr", "mot_de_passe": "motdepasse-solide", "accepte_cgu": True})
    assert r.status_code == 403


def test_retour_exige_un_compte(env):
    client, _, _ = env
    retour = {"reponse_id": "12345678-aaaa", "utile": True}
    assert client.post("/feedback", json=retour).status_code == 401
    inscrire(client)
    assert client.post("/feedback", json=retour).status_code == 204


def test_chat_exige_un_compte(env):
    client, _, _ = env
    assert client.post("/chat", json={"question": "article 1240"}).status_code == 401
    assert client.get("/sources/code_civil:A1240").status_code == 200   # les sources restent publiques
    assert client.get("/formules").json()[1]["id"] == "etudiant"


def test_quota_gratuit_et_remboursement(env):
    client, comptes, llm = env
    inscrire(client)
    llm.echec = True
    assert client.post("/chat", json={"question": "article 1240"}).status_code == 503
    assert client.get("/auth/moi").json()["usage"]["questions"] == 0      # echec du modele : pas decompte
    llm.echec = False
    for _ in range(10):
        assert client.post("/chat", json={"question": "article 1240"}).status_code == 200
    r = client.post("/chat", json={"question": "article 1240"})
    assert r.status_code == 402 and "Limite du jour" in r.json()["detail"]
    assert client.get("/auth/moi").json()["usage"]["questions"] == 10


def test_sans_extrait_ni_appel_au_modele_rien_n_est_decompte(tmp_path):
    class RetrieverVide(Retriever):
        def search(self, question, **kw):
            return []

    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=RetrieverVide(), llm=LLM(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    inscrire(client)
    assert client.post("/chat", json={"question": "question hors corpus"}).json()["statut"] == "abstention"
    assert client.post("/quiz", json={"theme": "theme hors corpus"}).json()["obtenu"] == 0
    assert client.get("/auth/moi").json()["usage"] | {"jour": None} == {"jour": None, "questions": 0, "quiz": 0}


def test_plafond_d_appels_modele_simultanes(tmp_path):
    import threading

    entre, libere = threading.Event(), threading.Event()

    class LLMLent(LLM):
        def generate_json(self, **kw):
            entre.set()
            libere.wait(5)
            return super().generate_json(**kw)

    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              appels_modele_simultanes=1),
                     retriever=Retriever(), llm=LLMLent(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    inscrire(client)
    premier = {}
    t = threading.Thread(target=lambda: premier.setdefault("r", client.post("/chat", json={"question": "article 1240"})))
    t.start()
    assert entre.wait(5)
    r = client.post("/chat", json={"question": "article 1240"})
    assert r.status_code == 503                                            # plafond atteint : refus immediat
    assert client.get("/auth/moi").json()["usage"]["questions"] == 1       # le refus n'est pas decompte
    libere.set()
    t.join(5)
    assert premier["r"].status_code == 200


def test_formule_payante_par_l_admin(env, tmp_path, monkeypatch, capsys):
    client, comptes, _ = env
    inscrire(client)
    monkeypatch.setenv("APP_DB", str(tmp_path / "comptes.db"))
    assert admin(["formule", "etu@exemple.fr", "etudiant", "--jours", "31"]) == 0
    moi = client.get("/auth/moi").json()
    assert moi["formule"]["id"] == "etudiant" and moi["formule"]["questions_par_jour"] == 100
    assert moi["formule_fin"] is not None
    assert admin(["formule", "inconnu@exemple.fr", "intensif"]) == 1
    assert admin(["liste"]) == 0 and "etu@exemple.fr" in capsys.readouterr().out


def test_nouveau_mot_de_passe_par_l_admin(env, tmp_path, monkeypatch):
    client, _, _ = env
    inscrire(client)
    monkeypatch.setenv("APP_DB", str(tmp_path / "comptes.db"))
    saisies = iter(["nouveau-mot-de-passe", "nouveau-mot-de-passe"])
    monkeypatch.setattr("getpass.getpass", lambda *_: next(saisies))
    assert admin(["motdepasse", "etu@exemple.fr"]) == 0
    assert client.get("/auth/moi").status_code == 401                     # sessions fermees
    connexion = lambda mdp: client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": mdp})  # noqa: E731
    assert connexion("motdepasse-solide").status_code == 401
    assert connexion("nouveau-mot-de-passe").status_code == 200
    saisies = iter(["un-mot-de-passe", "different-du-premier"])
    assert admin(["motdepasse", "etu@exemple.fr"]) == 1                   # confirmation differente


def test_formule_expiree_repasse_en_gratuit(tmp_path):
    comptes = Comptes(tmp_path / "c.db")
    comptes.creer("a@b.fr", "motdepasse-solide")
    u = comptes.changer_formule("a@b.fr", "intensif", jours=-1)
    assert u.formule.id == "gratuit"
    with pytest.raises(ErreurCompte):
        comptes.changer_formule("a@b.fr", "platine")


def test_numero_de_compte_jamais_reutilise(tmp_path):
    # Un compte cree apres une suppression ne reprend pas le numero : il heritait des limites gardees en
    # memoire par numero (echecs de double authentification), constate en ligne le 2026-11-16.
    chemin = tmp_path / "c.db"
    comptes = Comptes(chemin)
    a = comptes.creer("a@b.fr", "motdepasse-solide")
    b = comptes.creer("b@b.fr", "motdepasse-solide")
    comptes.supprimer(b.id)
    c = comptes.creer("c@b.fr", "motdepasse-solide")
    assert (a.id, b.id) == (1, 2) and c.id == 3
    comptes.supprimer(c.id)
    assert Comptes(chemin).creer("d@b.fr", "motdepasse-solide").id == 4    # compteur conserve en base
    # Base anterieure au compteur : on repart du plus grand numero existant.
    comptes._q("DELETE FROM compteurs")
    assert comptes.creer("e@b.fr", "motdepasse-solide").id == 5
    with pytest.raises(ErreurCompte):
        comptes.creer("e@b.fr", "motdepasse-solide")                    # doublon : message habituel


def test_suppression_du_compte(env):
    client, comptes, _ = env
    inscrire(client)
    client.post("/chat", json={"question": "article 1240"})
    assert client.post("/auth/supprimer", json={"mot_de_passe": "faux"}).status_code == 401
    assert client.post("/auth/supprimer", json={"mot_de_passe": "motdepasse-solide"}).status_code == 204
    assert comptes.par_email("etu@exemple.fr") is None
    assert client.get("/auth/moi").status_code == 401


def test_freins_aux_tentatives(env):
    client, _, _ = env
    inscrire(client)
    client.post("/auth/deconnexion")
    codes = [client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "faux"}).status_code
             for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_freins_oublient_les_adresses_expirees():
    """Chaque adresse essayee etait gardee en memoire jusqu'au redemarrage : un balayage d'e-mails
    faisait grossir le service sans fin."""
    import time

    from api.auth import Freins

    f = Freins()
    for i in range(300):
        f.verifier(f"10.0.{i // 100}.{i % 100}", f"inconnu{i}@exemple.fr")
        f.echec(f"inconnu{i}@exemple.fr")
    assert len(f._echecs) == 300
    f._derniere_purge = 0
    f._oublier(time.monotonic() + 16 * 60)  # la fenetre de 15 minutes est passee
    assert not f._echecs and not f._ip


def test_compte_supprime_absent_des_octets_de_la_base(tmp_path):
    """Audit de la base du 2026-11-18 : un compte supprime (adresse, empreinte, cours en cascade) ne doit
    plus etre lisible dans le fichier ni dans le journal WAL, comme un cours retire (audit C7)."""
    from pathlib import Path

    from api.cours import Cours

    def octets(chemin) -> bytes:
        return b"".join(Path(f"{chemin}{s}").read_bytes() for s in ("", "-wal") if Path(f"{chemin}{s}").exists())

    chemin = tmp_path / "lexia.db"
    comptes = Comptes(chemin)
    garde = comptes.creer("garde@b.fr", "motdepasse-solide")
    u = comptes.creer("zorglub.parti@b.fr", "motdepasse-solide")
    empreinte = comptes._q("SELECT mdp FROM utilisateurs WHERE id = ?", (u.id,))[0][0]
    Cours(chemin).ajouter(u.id, "droit_civil", "Cours", "c.txt", b"La theorie Zorglubienne du contrat. " * 40, 5)
    assert b"zorglub.parti@b.fr" in octets(chemin)
    comptes.supprimer(u.id, garder_trace=True)
    brut = octets(chemin)
    assert b"zorglub.parti@b.fr" not in brut
    assert empreinte.encode() not in brut
    assert b"zorglubienne" not in brut.lower()  # ni le texte, ni les mots de l'index plein texte
    assert comptes.par_id(garde.id) is not None



def test_rapatriement_ignore_les_copies_manuelles(tmp_path):
    """Une copie faite a la main dans le dossier des sauvegardes (lexia-avant-vacuum-AAAAMMJJ.db, le
    2026-11-18) passait apres les copies datees dans le tri par nom : prise pour la plus recente, elle
    faisait echouer le controle de fraicheur chaque jour, et n'etait jamais effacee sur le Mac."""
    import os
    import sqlite3
    import subprocess
    from datetime import date
    from pathlib import Path

    source, copies = tmp_path / "serveur", tmp_path / "mac"
    source.mkdir()
    jour = date.today().strftime("%Y%m%d")
    for nom in (f"lexia-{jour}.db", f"lexia-avant-vacuum-{jour}.db"):
        with sqlite3.connect(source / nom) as con:
            con.execute("CREATE TABLE utilisateurs (id INTEGER)")
    script = Path(__file__).resolve().parent.parent / "deploy" / "rapatrier_sauvegardes.sh"
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True,
                       env={**os.environ, "LEXIA_SERVEUR": "essai", "LEXIA_SOURCE": f"{source}/",
                            "LEXIA_COPIES": str(copies), "LEXIA_ESSAIS": "1"})
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in copies.iterdir()) == [f"lexia-{jour}.db"]
# --- prenom (D100) et nom (D102) ----------------------------------------------------------------------------

def inscrire_avec(client, **identite):
    return client.post("/auth/inscription", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide",
                                                  "accepte_cgu": True, **identite})


def test_prenom_et_nom_demandes_a_l_inscription(env):
    client, comptes, _ = env
    for manque in ({}, {"prenom": "Léa"}, {"nom": "Martin"}, {"prenom": "  ", "nom": "Martin"}):
        r = inscrire_avec(client, **manque)
        assert r.status_code == 422 and "prénom et votre nom" in r.json()["detail"], manque
    assert comptes.par_email("etu@exemple.fr") is None
    r = inscrire_avec(client, prenom="  Marie-Hélène  ", nom="de   La Fontaine")
    assert r.status_code == 201
    assert (r.json()["prenom"], r.json()["nom"]) == ("Marie-Hélène", "de La Fontaine")


def test_prenom_et_nom_modifiables_jamais_vides(env):
    client, comptes, _ = env
    inscrire(client)
    r = client.post("/auth/identite", json={"prenom": "Zoë", "nom": "d’Arc"})
    assert r.status_code == 200 and (r.json()["prenom"], r.json()["nom"]) == ("Zoë", "d’Arc")
    assert client.get("/auth/session").json()["nom"] == "d’Arc"
    assert client.post("/auth/identite", json={"prenom": "Zoë", "nom": " "}).status_code == 422
    for refuse in ("<script>", "Léa2", "a" * 51, "-Léa", "Léa\u0000"):
        assert client.post("/auth/identite", json={"prenom": refuse, "nom": "Martin"}).status_code == 422, refuse
        assert client.post("/auth/identite", json={"prenom": "Léa", "nom": refuse}).status_code == 422, refuse
    assert client.post("/auth/identite", json={"prenom": "x" * 101, "nom": "M"}).status_code == 422  # schema
    assert client.post("/auth/identite", json={"prenom": "Léa", "nom": "M"},
                       headers={"Origin": "https://pirate.exemple"}).status_code == 403
    assert comptes.identite(comptes.par_email("etu@exemple.fr").id) == ("Zoë", "d’Arc")
    client.post("/auth/deconnexion")
    assert client.post("/auth/identite", json={"prenom": "Léa", "nom": "M"}).status_code == 401


def test_compte_ancien_sans_identite_reste_utilisable(env):
    client, comptes, _ = env
    comptes.creer("ancien@exemple.fr", "motdepasse-solide")
    r = client.post("/auth/connexion", json={"email": "ancien@exemple.fr", "mot_de_passe": "motdepasse-solide"})
    assert r.status_code == 200 and r.json()["prenom"] is None and r.json()["nom"] is None
    assert client.post("/chat", json={"question": "article 1240"}).status_code == 200


def test_prenom_et_nom_jamais_envoyes_au_modele(env):
    client, _, llm = env
    appels = []
    generer = llm.generate_json
    llm.generate_json = lambda **kw: appels.append(kw) or generer(**kw)
    inscrire_avec(client, prenom="Bérénice", nom="Zorglubeau")
    assert client.post("/chat", json={"question": "article 1240"}).status_code == 200
    assert appels and "Bérénice" not in repr(appels) and "Zorglubeau" not in repr(appels)


def test_prenom_et_nom_effaces_avec_le_compte(env):
    client, comptes, _ = env
    inscrire_avec(client, prenom="Bérénice", nom="Zorglubeau")
    assert client.post("/auth/supprimer", json={"mot_de_passe": "motdepasse-solide"}).status_code == 204
    assert comptes._q("SELECT count(*) FROM utilisateurs WHERE prenom IS NOT NULL OR nom IS NOT NULL")[0][0] == 0


def test_migration_ajoute_prenom_et_nom(tmp_path):
    import sqlite3
    chemin = tmp_path / "ancienne.db"
    con = sqlite3.connect(chemin)
    con.executescript("CREATE TABLE utilisateurs (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, mdp TEXT NOT NULL,"
                      " formule TEXT NOT NULL DEFAULT 'gratuit', formule_fin TEXT, cree_le TEXT NOT NULL,"
                      " cgu_le TEXT NOT NULL);"
                      "INSERT INTO utilisateurs (email, mdp, cree_le, cgu_le) VALUES ('a@b.fr', 'x', '2026-01-01', '2026-01-01');")
    con.commit()
    con.close()
    c = Comptes(chemin)
    assert c.identite(1) == (None, None)
    assert c.changer_identite(1, "Léa", "Martin") == ("Léa", "Martin") and c.identite(1) == ("Léa", "Martin")


def test_questionnaire_sans_question_verifiable_non_decompte(env):
    """SRV-12 : le modele repond, mais aucune question ne passe le controle : rien a faire pour l'etudiant."""
    client, _, _ = env
    inscrire(client)
    r = client.post("/quiz", json={"theme": "la responsabilité"})
    assert r.status_code == 200 and r.json()["obtenu"] == 0 and r.json()["controle"]["modele_appele"]
    assert client.get("/auth/moi").json()["usage"]["quiz"] == 0


def test_remboursement_sur_le_jour_de_la_reservation(tmp_path, monkeypatch):
    """SRV-13 : une question reservee a 23 h 59 et ratee apres minuit etait rendue sur le lendemain."""
    from api import comptes as module
    comptes = Comptes(tmp_path / "c.db")
    u = comptes.creer("etu@exemple.fr", "motdepasse-solide", prenom="Léa", nom="Martin")
    monkeypatch.setattr(module, "_jour", lambda: "2026-11-19")
    jour = comptes.reserver(u, "questions")
    assert jour == "2026-11-19"
    monkeypatch.setattr(module, "_jour", lambda: "2026-11-20")
    comptes.rembourser(u, "questions", jour)
    monkeypatch.setattr(module, "_jour", lambda: "2026-11-19")
    assert comptes.usage(u.id)["questions"] == 0


def test_mots_de_passe_courants_refuses(env):
    """SEC-10 : aucun refus des mots de passe les plus essayes."""
    client, _, _ = env
    for mdp in ("azertyuiop", "Motdepasse123", "aaaaaaaaaaaa", "1212121212"):
        r = inscrire(client, mdp=mdp)
        assert r.status_code == 422 and "courant" in r.json()["detail"], mdp
    assert inscrire(client, mdp="ma-phrase-de-passe").status_code == 201
