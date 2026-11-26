"""D137 (audit du 25/11, S2) : le plafond d'echecs par compte ne bloque plus le titulaire sur un reseau connu."""

from datetime import timedelta

from fastapi.testclient import TestClient

from api import comptes as module_comptes
from api.export import donnees_du_compte
from tests.test_comptes import env, inscrire  # noqa: F401  (fixture partagee)

EMAIL, MDP = "etu@exemple.fr", "motdepasse-solide"


def connexion(client, mdp=MDP):
    return client.post("/auth/connexion", json={"email": EMAIL, "mot_de_passe": mdp})


def test_echecs_repartis_ne_bloquent_pas_un_reseau_connu(env):  # noqa: F811
    client, _, _ = env
    titulaire = TestClient(client.app, client=("2001:db8:1::5", 50000))
    assert inscrire(titulaire).status_code == 201
    titulaire.post("/auth/deconnexion")
    for n in range(10):                                         # 50 echecs, 5 par reseau /64
        attaquant = TestClient(client.app, client=(f"2001:db8:{n + 100:x}::1", 50000))
        for _ in range(5):
            assert connexion(attaquant, "faux-mot-de-passe").status_code == 401
    # Meme reseau /64, autre adresse : le titulaire se connecte...
    assert connexion(TestClient(client.app, client=("2001:db8:1::99", 50000))).status_code == 200
    # ...un reseau jamais vu reste soumis au plafond par compte, meme avec le bon mot de passe
    assert connexion(TestClient(client.app, client=("192.0.2.77", 50000))).status_code == 429
    # La connexion reussie du titulaire ne remet pas le plafond a zero pour les autres reseaux
    assert connexion(TestClient(client.app, client=("2001:db8:ff::1", 50000)), "x").status_code == 429


def test_reseau_garde_30_jours_en_empreinte(env, monkeypatch):  # noqa: F811
    client, comptes, _ = env
    assert inscrire(TestClient(client.app, client=("198.51.100.4", 50000))).status_code == 201
    uid = comptes.par_email(EMAIL).id
    with comptes._lock:
        lignes = comptes._con.execute("SELECT empreinte FROM reseaux_connus WHERE utilisateur = ?", (uid,)).fetchall()
    assert len(lignes) == 1 and "198.51.100" not in lignes[0][0]  # jamais l'adresse en clair
    assert comptes.reseau_connu(EMAIL, "198.51.100.4") and not comptes.reseau_connu(EMAIL, "198.51.100.5")
    depart = module_comptes._maintenant()
    monkeypatch.setattr(module_comptes, "_maintenant", lambda: depart + timedelta(days=29))
    assert comptes.reseau_connu(EMAIL, "198.51.100.4") and comptes.purger_reseaux() == 0
    monkeypatch.setattr(module_comptes, "_maintenant", lambda: depart + timedelta(days=30, minutes=1))
    assert not comptes.reseau_connu(EMAIL, "198.51.100.4")
    assert comptes.purger_reseaux() == 1


def test_reseaux_effaces_avec_le_compte(env):  # noqa: F811
    client, comptes, _ = env
    assert inscrire(TestClient(client.app, client=("198.51.100.4", 50000))).status_code == 201
    uid = comptes.par_email(EMAIL).id
    assert len(donnees_du_compte(comptes, uid)["reseaux_connus"]) == 1
    comptes.supprimer(uid, garder_trace=True)
    with comptes._lock:
        assert comptes._con.execute("SELECT COUNT(*) FROM reseaux_connus").fetchone()[0] == 0
    assert not comptes.reseau_connu(EMAIL, "198.51.100.4")
