"""Durees de conservation annoncees dans la politique de confidentialite (docs/registre-traitements.md)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from api import comptes as module_comptes
from api.comptes import Comptes


def test_trace_de_suppression_effacee_apres_24_h(tmp_path, monkeypatch):
    c = Comptes(tmp_path / "lexia.db")
    u = c.creer("etudiant@exemple.fr", "un mot de passe solide 2026")
    c.supprimer(u.id, garder_trace=True)
    assert c._q("SELECT count(*) FROM suppressions")[0][0] == 1

    c.purger_sessions()  # moins de 24 h : la trace reste (elle bloque la reinscription immediate)
    assert c._q("SELECT count(*) FROM suppressions")[0][0] == 1

    maintenant = module_comptes._maintenant()
    monkeypatch.setattr(module_comptes, "_maintenant", lambda: maintenant + timedelta(days=1, minutes=1))
    c.purger_sessions()
    assert c._q("SELECT count(*) FROM suppressions")[0][0] == 0


# --- comptes inactifs et compteurs d'usage (audit du 2026-11-18, E5) -----------------------------------------

from api import courriel  # noqa: E402
from api.paiement import Paiements  # noqa: E402


def _decaler(monkeypatch, jours: int) -> None:
    depart = module_comptes._maintenant()
    monkeypatch.setattr(module_comptes, "_maintenant", lambda: depart + timedelta(days=jours))


def _compte_ancien(c: Comptes, email: str, jours_inactif: int):
    u = c.creer(email, "un mot de passe solide 2026")
    c.confirmer_email(u.id)
    jour = module_comptes._jour_de(module_comptes._maintenant() - timedelta(days=jours_inactif))
    c._q("UPDATE utilisateurs SET actif_le = ? WHERE id = ?", (jour, u.id))
    return u


@pytest.fixture
def envois(monkeypatch):
    envoyes = []
    monkeypatch.setattr(courriel, "configure", lambda: True)
    monkeypatch.setattr(courriel, "envoyer", lambda dest, sujet, texte, html, jointes=None: envoyes.append((dest, sujet, texte)))
    return envoyes


def test_compteurs_d_usage_purges_apres_90_jours(tmp_path):
    c = Comptes(tmp_path / "lexia.db")
    u = c.creer("etudiant@exemple.fr", "un mot de passe solide 2026")
    aujourd_hui = module_comptes._maintenant()
    for jours in (0, 89, 91, 400):
        c._q("INSERT INTO usage (utilisateur, jour, questions) VALUES (?, ?, 1)",
             (u.id, module_comptes._jour_de(aujourd_hui - timedelta(days=jours))))
    assert c.purger_usage() == 2
    assert c._q("SELECT count(*) FROM usage")[0][0] == 2


def test_compte_inactif_averti_puis_supprime_sans_toucher_aux_paiements(tmp_path, monkeypatch, envois):
    c = Comptes(tmp_path / "lexia.db")
    paiements = Paiements(c)
    vieux = _compte_ancien(c, "ancien@exemple.fr", 701)
    recent = _compte_ancien(c, "recent@exemple.fr", 600)
    paiements.ouvrir("cs_test_1", vieux, "etudiant", 1, 499)
    c._q("UPDATE paiements SET statut = 'paye'")

    assert c.purger_inactifs() == {"avertis": 1, "supprimes": 0}
    assert [e[0] for e in envois] == ["ancien@exemple.fr"]
    assert "sera supprimé le" in envois[0][1]
    assert c.purger_inactifs() == {"avertis": 0, "supprimes": 0}  # un seul avertissement
    assert c.par_id(vieux.id) is not None

    _decaler(monkeypatch, 29)  # moins d'un mois apres l'avertissement : rien
    assert c.purger_inactifs()["supprimes"] == 0
    _decaler(monkeypatch, 31)
    assert c.purger_inactifs() == {"avertis": 0, "supprimes": 1}
    assert c.par_id(vieux.id) is None
    assert c.par_id(recent.id) is not None
    # la ligne de paiement, gardee pour la comptabilite, est intacte
    assert c._q("SELECT utilisateur, email, statut FROM paiements") == [(vieux.id, "ancien@exemple.fr", "paye")]


def test_une_connexion_annule_l_avertissement(tmp_path, monkeypatch, envois):
    c = Comptes(tmp_path / "lexia.db")
    u = _compte_ancien(c, "ancien@exemple.fr", 701)
    c.purger_inactifs()
    jeton = c.ouvrir_session(u.id)
    assert c._q("SELECT inactif_avis_le FROM utilisateurs WHERE id = ?", (u.id,)) == [(None,)]
    _decaler(monkeypatch, 20)  # session encore valide (30 jours)
    assert c.session(jeton) is not None
    _decaler(monkeypatch, 20)
    assert c.purger_inactifs() == {"avertis": 0, "supprimes": 0}
    assert c.par_id(u.id) is not None


def test_jamais_supprime_sans_avertissement_envoye(tmp_path, monkeypatch):
    c = Comptes(tmp_path / "lexia.db")
    monkeypatch.setattr(courriel, "configure", lambda: True)

    def refus(*_):
        raise courriel.ErreurCourriel("indisponible")
    monkeypatch.setattr(courriel, "envoyer", refus)
    u = _compte_ancien(c, "ancien@exemple.fr", 900)
    assert c.purger_inactifs() == {"avertis": 0, "supprimes": 0}
    _decaler(monkeypatch, 60)
    assert c.purger_inactifs() == {"avertis": 0, "supprimes": 0}
    assert c.par_id(u.id) is not None


def test_ni_administrateur_ni_formule_en_cours(tmp_path, monkeypatch, envois):
    c = Comptes(tmp_path / "lexia.db", admins=("admin@exemple.fr",))
    admin = _compte_ancien(c, "chef@exemple.fr", 900)
    c.definir_admin("chef@exemple.fr", True)
    declare = c.creer("admin@exemple.fr", "un mot de passe solide 2026", depuis_le_site=False)
    c._q("UPDATE utilisateurs SET actif_le = '2020-01-01' WHERE id = ?", (declare.id,))
    payant = _compte_ancien(c, "payant@exemple.fr", 900)
    c.changer_formule("payant@exemple.fr", "intensif", 365)
    offert = _compte_ancien(c, "offert@exemple.fr", 900)
    c.changer_formule("offert@exemple.fr", "etudiant")  # sans fin
    for _ in range(2):
        assert c.purger_inactifs() == {"avertis": 0, "supprimes": 0}
        _decaler(monkeypatch, 40)
    assert all(c.par_id(x.id) for x in (admin, declare, payant, offert))
    assert envois == []


def test_adresse_jamais_confirmee_supprimee_apres_deux_ans_sans_e_mail(tmp_path, envois):
    c = Comptes(tmp_path / "lexia.db")
    u = c.creer("inconnu@exemple.fr", "un mot de passe solide 2026")
    c._q("UPDATE utilisateurs SET actif_le = ?, email_verifie_le = NULL WHERE id = ?",
         (module_comptes._jour_de(module_comptes._maintenant() - timedelta(days=731)), u.id))
    assert c.purger_inactifs() == {"avertis": 0, "supprimes": 1}
    assert envois == []


def test_la_visite_du_jour_est_notee_une_fois(tmp_path, monkeypatch):
    c = Comptes(tmp_path / "lexia.db")
    monkeypatch.setattr(Comptes, "_entretien_si_nouveau_jour", lambda self: None)
    u = c.creer("etudiant@exemple.fr", "un mot de passe solide 2026")
    jeton = c.ouvrir_session(u.id)
    c._q("UPDATE utilisateurs SET actif_le = '2025-01-01' WHERE id = ?", (u.id,))
    c.session(jeton)
    assert c._q("SELECT actif_le FROM utilisateurs WHERE id = ?", (u.id,)) == \
        [(module_comptes._jour_de(module_comptes._maintenant()),)]


def test_migration_reprend_la_derniere_activite(tmp_path):
    chemin = tmp_path / "lexia.db"
    c = Comptes(chemin)
    u = c.creer("etudiant@exemple.fr", "un mot de passe solide 2026")
    c._q("INSERT INTO usage (utilisateur, jour, questions) VALUES (?, '2026-03-04', 1)", (u.id,))
    c._con.close()
    import sqlite3
    with sqlite3.connect(chemin) as con:  # base anterieure : sans les colonnes d'activite
        con.execute("ALTER TABLE utilisateurs DROP COLUMN inactif_avis_le")
        con.execute("ALTER TABLE utilisateurs DROP COLUMN actif_le")
    c = Comptes(chemin)
    assert c._q("SELECT actif_le FROM utilisateurs") == [("2026-03-04",)]


def test_jur12_questionnaires_effaces_avec_le_compte_et_purges_chaque_jour(tmp_path):
    """Audit du 2026-11-19, JUR-12 : questionnaires recopies en base (D5) jamais gardes au-dela de 3 h ni apres
    la suppression du compte."""
    import time as _time

    from api.comptes import QUESTIONNAIRES_CONSERVES_S, Comptes
    from api.quiz import TTL_SECONDES, Quiz, QuizStore

    assert QUESTIONNAIRES_CONSERVES_S == TTL_SECONDES
    comptes = Comptes(tmp_path / "comptes.db")
    a = comptes.creer("a@exemple.fr", "motdepasse-solide")
    b = comptes.creer("b@exemple.fr", "motdepasse-solide")
    store = QuizStore(chemin=comptes.chemin)
    for i, (uid, cree) in enumerate([(a.id, _time.time()), (b.id, _time.time()), (b.id, _time.time() - 4 * 3600)]):
        store._ecrire(Quiz(id=f"q{i}", format="qcm", theme="t", questions=[], table={}, cree=cree, proprietaire=uid))
    restants = lambda: sorted(r[0] for r in comptes._q("SELECT id FROM questionnaires"))  # noqa: E731
    assert comptes.purger_questionnaires() == 1 and restants() == ["q0", "q1"]
    comptes.supprimer(a.id)
    assert restants() == ["q1"]
