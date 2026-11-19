"""Verification de l'adresse e-mail : envoi, confirmation, blocage des questions."""

import sqlite3

import pytest

from api import courriel
from api.comptes import COLONNES_EMAIL, Comptes
from api.config import Settings
from api.main import create_app
from fastapi.testclient import TestClient
from tests.test_comptes import LLM, Retriever, inscrire


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Envoi configure : les e-mails partent vers une liste au lieu de Resend."""
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    envoyes: list[tuple[str, str]] = []
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: envoyes.append((dest, lien)))
    comptes = Comptes(tmp_path / "comptes.db")
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test"),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    return TestClient(app), comptes, envoyes


def jeton_de(lien: str) -> str:
    return lien.split("jeton=")[1]


def test_inscription_envoie_le_lien_et_bloque_les_questions(env):
    client, _, envoyes = env
    r = inscrire(client)
    assert r.status_code == 201 and r.json()["email_verifie"] is False
    assert len(envoyes) == 1 and envoyes[0][0] == "etu@exemple.fr"
    assert "/verifier-email#jeton=" in envoyes[0][1]

    # Tant que l'adresse n'est pas confirmee, aucune question n'est possible.
    r = client.post("/chat", json={"question": "Qu'est-ce que le dol ?", "mode": "expliquer",
                                   "matiere": None, "niveau": "L1", "semestre": 1})
    assert r.status_code == 403 and "Confirmez votre adresse" in r.json()["detail"]

    r = client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    assert r.status_code == 200 and r.json()["email_verifie"] is True
    assert client.post("/chat", json={"question": "Qu'est-ce que le dol ?", "mode": "expliquer",
                                      "matiere": None, "niveau": "L1", "semestre": 1}).status_code == 200


def test_jeton_invalide_ou_deja_utilise(env):
    client, _, envoyes = env
    inscrire(client)
    jeton = jeton_de(envoyes[0][1])
    assert client.post("/auth/email/verifier", json={"jeton": "inconnu"}).status_code == 422
    assert client.post("/auth/email/verifier", json={"jeton": jeton}).status_code == 200
    assert client.post("/auth/email/verifier", json={"jeton": jeton}).status_code == 422  # ne sert qu'une fois


def test_le_lien_confirme_sans_ouvrir_de_session(env):
    """Le lien contournait mot de passe et double authentification, et connectait la victime au compte
    d'un tiers inscrit avec son adresse (audit du 2026-11-16)."""
    client, _, envoyes = env
    inscrire(client)
    autre_appareil = TestClient(client.app)
    r = autre_appareil.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    assert r.status_code == 200 and r.json() is None
    assert "lexia_session" not in autre_appareil.cookies
    assert autre_appareil.get("/auth/session").json() is None
    assert client.get("/auth/session").json()["email_verifie"] is True       # l'adresse est bien confirmee


def test_faux_jetons_ne_bloquent_pas_les_autres_inscrits(env):
    """Le compteur d'echecs etait commun : 5 faux jetons bloquaient la confirmation pour tout le monde."""
    client, _, envoyes = env
    attaquant = TestClient(client.app, client=("203.0.113.9", 50000))
    for _ in range(6):
        attaquant.post("/auth/email/verifier", json={"jeton": "faux"})
    assert attaquant.post("/auth/email/verifier", json={"jeton": "faux"}).status_code == 429
    inscrire(client)
    assert client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])}).status_code == 200


def test_renvoi_limite_puis_refuse_si_deja_confirme(env):
    client, _, envoyes = env
    inscrire(client)
    # Un envoi vient d'avoir lieu (inscription) : le renvoi immediat est refuse.
    assert client.post("/auth/email/renvoyer").status_code == 429
    assert len(envoyes) == 1
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    assert client.post("/auth/email/renvoyer").status_code == 422  # deja confirmee


def test_sans_envoi_configure_rien_ne_bloque(tmp_path, monkeypatch):
    """Sans RESEND_API_KEY, la verification est desactivee : le site reste utilisable."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    comptes = Comptes(tmp_path / "comptes.db")
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test"),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    client = TestClient(app)
    assert inscrire(client).json()["email_verifie"] is True
    assert client.post("/chat", json={"question": "Qu'est-ce que le dol ?", "mode": "expliquer",
                                      "matiere": None, "niveau": "L1", "semestre": 1}).status_code == 200


def test_comptes_anterieurs_restent_utilisables(tmp_path, monkeypatch):
    """Une base d'avant la verification (colonnes absentes) : ses comptes sont consideres confirmes,
    sinon la mise a jour bloquerait tout le monde du jour au lendemain."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    chemin = tmp_path / "comptes.db"
    u = Comptes(chemin).creer("ancien@exemple.fr", "motdepasse-solide")
    con = sqlite3.connect(chemin)  # on retire les colonnes pour retrouver l'etat d'avant
    for colonne in COLONNES_EMAIL:
        con.execute(f"ALTER TABLE utilisateurs DROP COLUMN {colonne}")
    con.commit()
    con.close()

    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    assert Comptes(chemin).par_id(u.id).email_verifie is True


def test_le_lien_ne_suit_jamais_l_en_tete_host(env):
    """Un domaine tiers pointe sur le serveur faisait envoyer, depuis l'adresse de Lexia, des liens vers lui."""
    client, _, envoyes = env
    client.post("/auth/inscription", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide",
                                           "accepte_cgu": True, "prenom": "Léa", "nom": "Martin"},
                headers={"Host": "pirate.example", "Origin": "https://pirate.example"})
    assert envoyes and envoyes[0][1].startswith("https://lexia.test/verifier-email#jeton=")


def test_sans_url_publique_aucun_lien_n_est_envoye(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    envoyes = []
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: envoyes.append(lien))
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "c.db"))
    assert inscrire(TestClient(app)).status_code == 201 and envoyes == []


def test_renvois_plafonnes_par_compte(env, monkeypatch):
    """Sans plafond, un compte inscrit a l'adresse d'un tiers lui envoyait 720 e-mails par jour (audit 2, point 4)."""
    client, comptes, envoyes = env
    inscrire(client)
    monkeypatch.setattr(comptes, "jeton_verification", lambda uid, force=False: "jeton")  # sans les 2 minutes d'ecart
    codes = [client.post("/auth/email/renvoyer").status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]
    assert len(envoyes) == 1 + 5


def test_adresse_squattee_reprise_apres_le_delai_du_lien(env, tmp_path):
    """Un compte cree avec l'adresse d'un tiers et jamais confirme bloquait a vie son inscription (audit 2, point 6)."""
    client, comptes, envoyes = env
    squatteur = TestClient(client.app)
    inscrire(squatteur, mdp="mot-de-passe-du-squatteur")
    assert inscrire(TestClient(client.app)).status_code == 422          # avant 24 h : l'adresse reste prise
    with sqlite3.connect(comptes.chemin) as c:                          # 25 h plus tard
        c.execute("UPDATE utilisateurs SET cree_le = '2000-01-01T00:00:00+00:00'")
    titulaire = TestClient(client.app)
    assert inscrire(titulaire).status_code == 201                       # le vrai titulaire s'inscrit
    assert squatteur.get("/auth/moi").status_code == 401                # la session du squatteur est fermee
    r = titulaire.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"})
    assert r.status_code == 200


def test_compte_confirme_jamais_remplace(env):
    client, comptes, envoyes = env
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    with sqlite3.connect(comptes.chemin) as c:
        c.execute("UPDATE utilisateurs SET cree_le = '2000-01-01T00:00:00+00:00'")
    assert inscrire(TestClient(client.app), mdp="autre-mot-de-passe").status_code == 422


# --- mot de passe oublie --------------------------------------------------------

def _liens_oubli(monkeypatch):
    liens = []
    monkeypatch.setattr(courriel, "envoyer_reinitialisation", lambda dest, lien: liens.append((dest, lien)))
    return liens


def _attendre(liste, n=1):
    import time
    for _ in range(100):
        if len(liste) >= n:
            return
        time.sleep(0.02)


def test_mot_de_passe_oublie_de_bout_en_bout(env, monkeypatch):
    client, _, envoyes = env
    liens = _liens_oubli(monkeypatch)
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    autre = TestClient(client.app)
    # Meme reponse pour une adresse inconnue : la page ne dit pas qui est inscrit.
    assert autre.post("/auth/mot-de-passe/oubli", json={"email": "inconnu@exemple.fr"}).json() == {"envoye": True}
    assert autre.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"}).json() == {"envoye": True}
    _attendre(liens)
    assert len(liens) == 1 and liens[0][0] == "etu@exemple.fr"
    assert liens[0][1].startswith("https://lexia.test/nouveau-mot-de-passe#jeton=")
    jeton = liens[0][1].split("jeton=")[1]
    assert autre.post("/auth/mot-de-passe/nouveau", json={"jeton": jeton, "mot_de_passe": "court"}).status_code == 422
    r = autre.post("/auth/mot-de-passe/nouveau", json={"jeton": jeton, "mot_de_passe": "nouveau-mot-de-passe"})
    assert r.status_code == 200 and "lexia_session" not in autre.cookies          # le lien n'ouvre pas de session
    assert client.get("/auth/moi").status_code == 401                             # anciennes sessions fermees
    assert autre.post("/auth/mot-de-passe/nouveau", json={"jeton": jeton, "mot_de_passe": "encore-un-autre"}).status_code == 422
    assert autre.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"}).status_code == 401
    assert autre.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "nouveau-mot-de-passe"}).status_code == 200


def test_le_titulaire_reprend_une_adresse_squattee(env, monkeypatch):
    """Un tiers a cree le compte avec l'adresse de la victime et active sa double authentification : le lien
    recu dans la vraie boite rend l'adresse a son titulaire (second audit, point 6)."""
    from api import totp
    client, comptes, _ = env
    liens = _liens_oubli(monkeypatch)
    squatteur = TestClient(client.app)
    inscrire(squatteur, mdp="mot-de-passe-du-squatteur")
    secret = squatteur.post("/auth/2fa/preparer").json()["secret"]
    squatteur.post("/auth/2fa/activer", json={"mot_de_passe": "mot-de-passe-du-squatteur",
                                              "code": totp._code(secret, totp.etape_courante())})
    titulaire = TestClient(client.app)
    titulaire.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"})
    _attendre(liens)
    titulaire.post("/auth/mot-de-passe/nouveau", json={"jeton": liens[0][1].split("jeton=")[1],
                                                       "mot_de_passe": "le-vrai-mot-de-passe"})
    r = titulaire.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "le-vrai-mot-de-passe"})
    assert r.status_code == 200 and r.json()["email_verifie"] is True       # adresse confirmee par le lien
    assert r.json()["double_authentification"] is False                    # celle du squatteur est retiree
    assert squatteur.get("/auth/moi").status_code == 401


def test_un_compte_confirme_garde_sa_double_authentification(env, monkeypatch):
    from api import totp
    client, _, envoyes = env
    liens = _liens_oubli(monkeypatch)
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    client.post("/auth/2fa/activer", json={"mot_de_passe": "motdepasse-solide",
                                           "code": totp._code(secret, totp.etape_courante())})
    client.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"})
    _attendre(liens)
    client.post("/auth/mot-de-passe/nouveau", json={"jeton": liens[0][1].split("jeton=")[1],
                                                    "mot_de_passe": "nouveau-mot-de-passe"})
    r = client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "nouveau-mot-de-passe"})
    assert r.json().get("double_authentification_requise") is True          # le lien seul ne suffit pas a entrer


def _sans_delai_entre_liens(monkeypatch):
    import datetime
    from api import comptes as module_comptes
    monkeypatch.setattr(module_comptes, "DELAI_ENTRE_ENVOIS", datetime.timedelta(0))


def _inscrit_confirme(app, envoyes, email, ip):
    c = TestClient(app, client=(ip, 50000))
    inscrire(c, email=email)
    lien = next(l for d, l in reversed(envoyes) if d == email)
    assert c.post("/auth/email/verifier", json={"jeton": jeton_de(lien)}).status_code == 200


def test_des_comptes_inventes_ne_privent_pas_les_etudiants_de_leur_lien(env, monkeypatch):
    """SEC-1 (TST-10) : 10 comptes non confirmes x 5 « mot de passe oublie » epuisaient le plafond commun de 50 ;
    pendant 24 h, un etudiant confirme lisait « envoye » sans recevoir aucun e-mail."""
    from api import auth
    client, _, envoyes = env
    liens = _liens_oubli(monkeypatch)
    _sans_delai_entre_liens(monkeypatch)
    _inscrit_confirme(client.app, envoyes, "etu@exemple.fr", "192.0.2.1")
    pirates = [TestClient(client.app, client=(f"10.0.0.{k}", 50000)) for k in range(10)]   # une IP chacun
    for k, pirate in enumerate(pirates):
        inscrire(pirate, email=f"invente{k}@exemple.fr")
    for k, pirate in enumerate(pirates):
        for _ in range(5):
            assert pirate.post("/auth/mot-de-passe/oubli", json={"email": f"invente{k}@exemple.fr"}).json() == {
                "envoye": True}
    attendus = auth.ENVOIS_NON_CONFIRMES_JOUR - len(envoyes)    # les liens d'inscription comptent aussi
    _attendre(liens, attendus)
    assert len(liens) == attendus and len(envoyes) == 11
    etudiant = TestClient(client.app, client=("192.0.2.1", 50000))
    assert etudiant.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"}).json() == {"envoye": True}
    _attendre(liens, attendus + 1)
    assert liens[-1][0] == "etu@exemple.fr"


def test_liens_mot_de_passe_oublie_plafonnes_par_ip(env, monkeypatch):
    from api import auth
    client, _, envoyes = env
    liens = _liens_oubli(monkeypatch)
    _sans_delai_entre_liens(monkeypatch)
    for k in range(3):
        _inscrit_confirme(client.app, envoyes, f"etu{k}@exemple.fr", f"192.0.2.{k}")
    meme_ip = TestClient(client.app, client=("198.51.100.7", 50000))
    for k in range(3):
        for _ in range(auth.RENVOIS_PAR_COMPTE_JOUR):
            meme_ip.post("/auth/mot-de-passe/oubli", json={"email": f"etu{k}@exemple.fr"})
    _attendre(liens, auth.OUBLIS_PAR_IP_JOUR + 1)
    assert len(liens) == auth.OUBLIS_PAR_IP_JOUR
    autre_ip = TestClient(client.app, client=("198.51.100.8", 50000))
    autre_ip.post("/auth/mot-de-passe/oubli", json={"email": "etu2@exemple.fr"})
    _attendre(liens, auth.OUBLIS_PAR_IP_JOUR + 1)
    assert len(liens) == auth.OUBLIS_PAR_IP_JOUR + 1


def test_codes_2fa_faux_plafonnes_sur_24_h_et_titulaire_prevenu(env, monkeypatch):
    """SEC-2 : 5 echecs par 15 minutes seulement, remis a zero par chaque connexion reussie ; personne prevenu."""
    import pytest
    from fastapi import HTTPException
    from api import auth, totp
    client, _, envoyes = env
    alertes = []
    monkeypatch.setattr(courriel, "envoyer_alerte_code_faux", lambda dest: alertes.append(dest))
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    client.post("/auth/2fa/activer", json={"mot_de_passe": "motdepasse-solide",
                                           "code": totp._code(secret, totp.etape_courante())})
    autre = TestClient(client.app)
    for _ in range(2):
        jeton = autre.post("/auth/connexion", json={"email": "etu@exemple.fr",
                                                    "mot_de_passe": "motdepasse-solide"}).json()["jeton"]
        assert autre.post("/auth/connexion/code", json={"jeton": jeton, "code": "zzzz-zzzz"}).status_code == 401
    _attendre(alertes)
    assert alertes == ["etu@exemple.fr"]                 # une seule alerte par 24 h

    f = auth.Freins()
    for _ in range(20):
        f.verifier_jour("2fa:1")
        f.echec_jour("2fa:1")
    f.succes("2fa:1")                                    # une connexion reussie ne remet pas ce compteur a zero
    with pytest.raises(HTTPException) as e:
        f.verifier_jour("2fa:1")
    assert e.value.status_code == 429
