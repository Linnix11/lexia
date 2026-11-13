"""Chiffrement des secrets gardes en base (api/coffre.py) et son effet sur les comptes."""

import sqlite3

import pytest

from api import coffre, totp
from api.comptes import Comptes

CLE = "0wPQ3zGZ2m4GH0DWyvo8ZC_LtLz3hkC2hT0rWUxWmdM="  # cle de test, jamais en production


@pytest.fixture
def avec_cle(monkeypatch):
    monkeypatch.setenv(coffre.VARIABLE, CLE)


@pytest.fixture
def sans_cle(monkeypatch):
    monkeypatch.delenv(coffre.VARIABLE, raising=False)


def test_aller_retour(avec_cle):
    scelle = coffre.chiffrer("JBSWY3DPEHPK3PXP")
    assert scelle.startswith(coffre.PREFIXE) and "JBSWY3DPEHPK3PXP" not in scelle
    assert coffre.dechiffrer(scelle) == "JBSWY3DPEHPK3PXP"
    assert coffre.chiffrer(None) is None and coffre.dechiffrer(None) is None
    assert coffre.chiffrer("x") != coffre.chiffrer("x")  # nonce different a chaque fois


def test_valeur_modifiee_refusee(avec_cle):
    scelle = coffre.chiffrer("secret")
    abime = scelle[:-3] + ("aaa" if not scelle.endswith("aaa") else "bbb")
    with pytest.raises(coffre.ErreurCoffre):
        coffre.dechiffrer(abime)


def test_autre_cle_refusee(avec_cle, monkeypatch):
    scelle = coffre.chiffrer("secret")
    monkeypatch.setenv(coffre.VARIABLE, coffre.nouvelle_cle())
    with pytest.raises(coffre.ErreurCoffre):
        coffre.dechiffrer(scelle)


def test_cle_illisible(monkeypatch):
    monkeypatch.setenv(coffre.VARIABLE, "trop-court")
    with pytest.raises(coffre.ErreurCoffre):
        coffre.chiffrer("secret")


def test_sans_cle_les_valeurs_restent_en_clair(sans_cle):
    assert not coffre.cle_configuree()
    assert coffre.chiffrer("secret") == "secret"
    assert coffre.dechiffrer("secret") == "secret"
    with pytest.raises(coffre.ErreurCoffre):  # une base deja chiffree exige sa cle
        coffre.dechiffrer(coffre.PREFIXE + "abc")


def code(secret, decalage=0):
    """Decalage 1 : le code de la periode suivante, accepte (fenetre +/-1) mais jamais deja utilise."""
    return totp._code(secret, totp.etape_courante() + decalage)


def test_les_secrets_2fa_sont_chiffres_en_base(avec_cle, tmp_path):
    comptes = Comptes(tmp_path / "comptes.db")
    u = comptes.creer("etu@exemple.fr", "motdepasse-solide")
    secret = comptes.preparer_2fa(u.id)
    secours = comptes.activer_2fa(u.id, code(secret))

    brut = sqlite3.connect(tmp_path / "comptes.db").execute(
        "SELECT totp_secret, totp_attente, totp_secours FROM utilisateurs WHERE id = ?", (u.id,)).fetchone()
    assert brut[0].startswith(coffre.PREFIXE) and secret not in brut[0]
    assert brut[1] is None
    assert brut[2].startswith(coffre.PREFIXE) and totp.empreinte_secours(secours[0]) not in brut[2]

    assert comptes.verifier_2fa(u.id, code(secret, 1))       # l'application fonctionne
    assert comptes.codes_secours_restants(u.id) == 8
    assert comptes.verifier_2fa(u.id, secours[0])            # un code de secours aussi
    assert comptes.codes_secours_restants(u.id) == 7


def test_base_ancienne_chiffree_au_demarrage(sans_cle, tmp_path, monkeypatch):
    """Une base ecrite avant le chiffrement continue de fonctionner, et ses secrets sont reecrits."""
    chemin = tmp_path / "comptes.db"
    comptes = Comptes(chemin)
    u = comptes.creer("etu@exemple.fr", "motdepasse-solide")
    secret = comptes.preparer_2fa(u.id)
    comptes.activer_2fa(u.id, code(secret))
    clair = sqlite3.connect(chemin).execute("SELECT totp_secret FROM utilisateurs").fetchone()[0]
    assert clair == secret  # sans cle : en clair, comme avant

    monkeypatch.setenv(coffre.VARIABLE, CLE)
    comptes2 = Comptes(chemin)  # le demarrage suivant chiffre ce qui restait lisible
    chiffre = sqlite3.connect(chemin).execute("SELECT totp_secret FROM utilisateurs").fetchone()[0]
    assert chiffre.startswith(coffre.PREFIXE) and secret not in chiffre
    assert comptes2.verifier_2fa(u.id, code(secret, 1))
