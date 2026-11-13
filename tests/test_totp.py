"""Double authentification par application (TOTP, RFC 6238)."""

from api import totp
from tests.test_comptes import env, inscrire  # noqa: F401  (fixture partagee)

SECRET_RFC = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # « 12345678901234567890 » en base32 (RFC 6238, annexe B)


def test_vecteurs_rfc_6238():
    assert totp._code(SECRET_RFC, 59 // 30)[-6:] == "287082"
    assert totp._code(SECRET_RFC, 1111111109 // 30) == "081804"
    assert totp.verifier(SECRET_RFC, "287 082", maintenant=59) == 1


def test_code_deja_utilise_refuse():
    etape = totp.verifier(SECRET_RFC, "287082", maintenant=59)
    assert totp.verifier(SECRET_RFC, "287082", derniere_etape=etape, maintenant=59) is None
    assert totp.verifier(SECRET_RFC, "12345", maintenant=59) is None


def code(secret):
    return totp._code(secret, totp.etape_courante())


def test_activation_connexion_secours_desactivation(env):  # noqa: F811
    client, comptes, _ = env
    inscrire(client)
    assert client.get("/auth/moi").json()["double_authentification"] is False
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    assert client.post("/auth/2fa/activer", json={"code": "000000" if code(secret) != "000000" else "111111"}).status_code == 422
    r = client.post("/auth/2fa/activer", json={"code": code(secret)})
    assert r.status_code == 200
    secours = r.json()["codes_secours"]
    assert len(secours) == 8
    moi = client.get("/auth/moi").json()
    assert moi["double_authentification"] is True and moi["codes_secours_restants"] == 8

    # Connexion : le mot de passe seul n'ouvre plus de session.
    client.post("/auth/deconnexion")
    r = client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"})
    assert r.json()["double_authentification_requise"] is True and "set-cookie" not in r.headers
    assert client.get("/auth/moi").status_code == 401
    jeton = r.json()["jeton"]
    assert client.post("/auth/connexion/code", json={"jeton": jeton, "code": "abc"}).status_code >= 400
    r = client.post("/auth/connexion/code", json={"jeton": jeton, "code": secours[0]})
    assert r.status_code == 200 and client.get("/auth/moi").json()["codes_secours_restants"] == 7

    # Un code de secours ne sert qu'une fois.
    client.post("/auth/deconnexion")
    jeton = client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"}).json()["jeton"]
    assert client.post("/auth/connexion/code", json={"jeton": jeton, "code": secours[0]}).status_code >= 400
    assert client.post("/auth/connexion/code", json={"jeton": jeton, "code": secours[1]}).status_code == 200



def test_desactivation(env):  # noqa: F811
    client, _, _ = env
    inscrire(client)
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    secours = client.post("/auth/2fa/activer", json={"code": code(secret)}).json()["codes_secours"]
    # Desactivation : mot de passe et code exiges.
    assert client.post("/auth/2fa/desactiver", json={"mot_de_passe": "faux", "code": secours[2]}).status_code >= 400
    r = client.post("/auth/2fa/desactiver", json={"mot_de_passe": "motdepasse-solide", "code": secours[3]})
    assert r.status_code == 200 and r.json()["double_authentification"] is False
    client.post("/auth/deconnexion")
    r = client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"})
    assert r.json()["email"] == "etu@exemple.fr"


def test_jeton_limite_en_essais(env):  # noqa: F811
    client, _, _ = env
    inscrire(client)
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    client.post("/auth/2fa/activer", json={"code": code(secret)})
    client.post("/auth/deconnexion")
    jeton = client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"}).json()["jeton"]
    for _ in range(5):
        client.post("/auth/connexion/code", json={"jeton": jeton, "code": "zzzz-zzzz"})
    # Apres 5 essais le jeton est detruit, meme un bon code est refuse.
    assert client.post("/auth/connexion/code", json={"jeton": jeton, "code": "zzzz-zzzz"}).status_code >= 400
