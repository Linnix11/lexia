"""Securite (audit du 23/11, lot B) : budgets d'e-mails (B1, B6 ; T11), codes 2FA (B2, B7 ; T12), lecteur de
fichiers (B8), octet nul et mots de passe courants (B10)."""

import sys
import time

import pytest
from fastapi.testclient import TestClient

from api import auth, courriel, extraction, totp
from api.comptes import Comptes, ErreurCompte
from api.config import Settings
from api.main import create_app
from tests.test_comptes import LLM, Retriever, inscrire
from tests.test_serveur import _serveur
from tests.test_verification_email import _attendre, _liens_oubli, _sans_delai_entre_liens, jeton_de


def _app(comptes, tmp_path):
    return create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                               url_publique="https://lexia.test"),
                      retriever=Retriever(), llm=LLM(), comptes=comptes)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    envoyes: list[tuple[str, str]] = []
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: envoyes.append((dest, lien)))
    comptes = Comptes(tmp_path / "comptes.db")
    return _app(comptes, tmp_path), comptes, envoyes, tmp_path


# --- B1 / T11 : plafond par adresse des liens d'inscription et de renvoi ---------------------------------------

def test_t11_liens_d_inscription_plafonnes_par_adresse(env):
    app, comptes, envoyes, _ = env
    for k in range(auth.LIENS_PAR_IP_JOUR + 2):
        r = inscrire(TestClient(app, client=("198.51.100.7", 50000)), email=f"invente{k}@exemple.fr")
        assert r.status_code == 201                          # le compte est cree dans tous les cas
        assert r.json()["lien_envoye"] is (k < auth.LIENS_PAR_IP_JOUR)
    assert len(envoyes) == auth.LIENS_PAR_IP_JOUR            # avant : 5, chacun pris sur le budget commun
    etudiant = TestClient(app, client=("192.0.2.1", 50000))
    assert inscrire(etudiant).json()["lien_envoye"] is True  # une autre adresse recoit son lien


def test_t11_ipv6_plafond_par_reseau_48(env):
    app, _, envoyes, _ = env
    for k in range(auth.LIENS_PAR_IP_JOUR + 2):             # un /64 different a chaque fois, meme /48
        inscrire(TestClient(app, client=(f"2001:db8:0:{k:x}::1", 50000)), email=f"v6-{k}@exemple.fr")
    assert len(envoyes) == auth.LIENS_PAR_IP_JOUR


def test_t11_renvois_plafonnes_par_adresse(env, monkeypatch):
    app, comptes, envoyes, _ = env
    _sans_delai_entre_liens(monkeypatch)
    statuts = []
    for k in range(auth.LIENS_PAR_IP_JOUR + 1):
        c = TestClient(app, client=(f"10.0.0.{k}", 50000))   # inscriptions depuis des adresses differentes
        inscrire(c, email=f"r{k}@exemple.fr")
        meme = TestClient(app, client=("198.51.100.9", 50000), cookies=c.cookies)
        statuts.append(meme.post("/auth/email/renvoyer").status_code)
    assert statuts == [202] * auth.LIENS_PAR_IP_JOUR + [429]


def test_t11_mot_de_passe_oublie_deux_liens_par_compte(env, monkeypatch):
    app, comptes, envoyes, _ = env
    liens = _liens_oubli(monkeypatch)
    _sans_delai_entre_liens(monkeypatch)
    c = TestClient(app, client=("192.0.2.1", 50000))
    inscrire(c)
    c.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    for k in range(4):                                        # depuis 4 adresses : seul le compte plafonne
        TestClient(app, client=(f"203.0.113.{k}", 50000)).post("/auth/mot-de-passe/oubli",
                                                                 json={"email": "etu@exemple.fr"})
    _attendre(liens, 3)
    time.sleep(0.1)
    assert len(liens) == auth.OUBLIS_PAR_COMPTE_JOUR          # avant : 4 (5 par compte)


# --- B6 / T11 : budgets conserves apres un redemarrage ----------------------------------------------------------

def test_t11_budgets_conserves_apres_un_redemarrage(env, monkeypatch):
    app, comptes, envoyes, tmp_path = env
    monkeypatch.setattr(auth, "ENVOIS_NON_CONFIRMES_JOUR", 2)
    for k in range(2):
        inscrire(TestClient(app, client=(f"10.1.0.{k}", 50000)), email=f"a{k}@exemple.fr")
    assert len(envoyes) == 2
    relance = _app(Comptes(tmp_path / "comptes.db"), tmp_path)   # redemarrage du service : meme base
    r = inscrire(TestClient(relance, client=("10.1.0.9", 50000)), email="apres@exemple.fr")
    assert r.json()["lien_envoye"] is False and len(envoyes) == 2  # avant : budget remis a zero, 3 envois


def test_compteurs_fenetre_de_24_h_et_cles_hachees(tmp_path):
    t = [1_000_000.0]
    c = auth.Compteurs(tmp_path / "c.db", horloge=lambda: t[0])
    assert c.reserver(("ip:192.0.2.1", 2)) and c.reserver(("ip:192.0.2.1", 2))
    assert c.reserver(("ip:192.0.2.1", 2)) is None
    t[0] += 86401
    assert c.reserver(("ip:192.0.2.1", 2))                     # fenetre passee
    import sqlite3
    cles = [r[0] for r in sqlite3.connect(tmp_path / "c.db").execute("SELECT cle FROM compteurs_jour")]
    assert cles and not any("192.0.2.1" in k for k in cles)    # aucune adresse en clair


# --- B2 / T12 : plafond du jour atteint, un code de secours valide passe encore -----------------------------------

def _compte_2fa(app, envoyes):
    client = TestClient(app)
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    codes = client.post("/auth/2fa/activer", json={"mot_de_passe": "motdepasse-solide",
                                                   "code": totp._code(secret, totp.etape_courante())}).json()
    return client, secret, codes["codes_secours"]


def _jeton(app):
    return TestClient(app).post("/auth/connexion", json={"email": "etu@exemple.fr",
                                                        "mot_de_passe": "motdepasse-solide"}).json()["jeton"]


def test_t12_plafond_atteint_code_de_secours_accepte(env, monkeypatch):
    app, comptes, envoyes, _ = env
    monkeypatch.setattr(courriel, "envoyer_alerte_code_faux", lambda dest: None)
    _, secret, secours = _compte_2fa(app, envoyes)
    uid = comptes.par_email("etu@exemple.fr").id
    compteurs = auth.Compteurs(comptes.chemin)
    for _ in range(auth.ECHECS_2FA_JOUR):                     # 20 codes faux deja comptes aujourd'hui
        compteurs.ajouter(f"2fa:{uid}")
    c = TestClient(app)
    r = c.post("/auth/connexion/code", json={"jeton": _jeton(app), "code": totp._code(secret, totp.etape_courante())})
    assert r.status_code == 429 and "code de secours" in r.json()["detail"]
    r = c.post("/auth/connexion/code", json={"jeton": _jeton(app), "code": secours[0]})
    assert r.status_code == 200 and r.json()["email"] == "etu@exemple.fr"   # avant : 429
    r = c.post("/auth/connexion/code", json={"jeton": _jeton(app), "code": "zzzz-zzzz"})
    assert r.status_code == 401                               # un faux code de secours reste refuse


def test_t12_plafond_conserve_apres_un_redemarrage(env, monkeypatch):
    app, comptes, envoyes, tmp_path = env
    monkeypatch.setattr(courriel, "envoyer_alerte_code_faux", lambda dest: None)
    monkeypatch.setattr(auth, "ECHECS_2FA_JOUR", 3)
    app = _app(comptes, tmp_path)                             # plafond lu a la creation des routes
    _compte_2fa(app, envoyes)
    for k in range(3):
        c = TestClient(app, client=(f"10.2.0.{k}", 50000))   # adresses differentes : pas le frein par 15 min
        assert c.post("/auth/connexion/code", json={"jeton": _jeton(app), "code": "000000"}).status_code == 401
    relance = _app(Comptes(tmp_path / "comptes.db"), tmp_path)
    r = TestClient(relance, client=("10.2.0.9", 50000)).post(
        "/auth/connexion/code", json={"jeton": _jeton(relance), "code": "000000"})
    assert r.status_code == 429                               # avant : remis a zero par le redemarrage


# --- B7 : desactivation de la 2FA et suppression dans le plafond du jour, titulaire prevenu -------------------------

def test_b7_desactiver_et_supprimer_comptent_les_codes_faux_et_previennent(env, monkeypatch):
    app, comptes, envoyes, _ = env
    alertes = []
    monkeypatch.setattr(courriel, "envoyer_alerte_code_faux", lambda dest: alertes.append(dest))
    client, _, _ = _compte_2fa(app, envoyes)
    uid = comptes.par_email("etu@exemple.fr").id
    r = client.post("/auth/2fa/desactiver", json={"mot_de_passe": "motdepasse-solide", "code": "000000"})
    assert r.status_code == 401
    r = client.post("/auth/supprimer", json={"mot_de_passe": "motdepasse-solide", "code": "000000"})
    assert r.status_code == 401
    assert auth.Compteurs(comptes.chemin).compter(f"2fa:{uid}") == 2   # avant : 0
    _attendre(alertes)
    assert alertes == ["etu@exemple.fr"]                     # avant : aucune alerte


# --- B8 : dossier temporaire du lecteur supprime meme quand il est tue ------------------------------------------------

def test_b8_dossier_temporaire_supprime_quand_le_lecteur_est_tue(monkeypatch):
    dossiers = []
    vrai = extraction.tempfile.mkdtemp

    def note(*a, **kw):
        d = vrai(*a, **kw)
        dossiers.append(d)
        return d
    monkeypatch.setattr(extraction.tempfile, "mkdtemp", note)
    # Lecteur qui ecrit le cours dans son dossier temporaire puis reste bloque (comme un OCR trop long)
    script = ("import sys, tempfile, time, pathlib; sys.stdin.buffer.read(); "
              "pathlib.Path(tempfile.gettempdir(), 'cours.pdf').write_bytes(b'cours'); time.sleep(30)")
    monkeypatch.setattr(extraction, "_commande_lecteur", lambda nom: [sys.executable, "-c", script])
    with pytest.raises(extraction.ErreurCours):
        extraction.lire_isole("cours.pdf", b"%PDF-1.4", delai=1.5)
    assert len(dossiers) == 1
    from pathlib import Path
    assert not Path(dossiers[0]).exists()                    # avant : le cours restait dans /tmp


# --- B10 --------------------------------------------------------------------------------------------------------------

def test_b10_octet_nul_dans_le_chemin_refuse_sans_erreur_500(tmp_path):
    assert _serveur(tmp_path).get("/abc%00def").status_code == 400


@pytest.mark.parametrize("mdp", ["soleil2026!", "13marseille13", "Azerty2025", "4815162342", "motdepasse!!!"])
def test_b10_mots_courants_entoures_de_chiffres_refuses(tmp_path, mdp):
    with pytest.raises(ErreurCompte, match="trop courant"):
        Comptes(tmp_path / "c.db").creer("x@exemple.fr", mdp)


def test_b10_phrase_de_passe_acceptee(tmp_path):
    assert Comptes(tmp_path / "c.db").creer("x@exemple.fr", "soleil-sur-la-mer-2026").id
