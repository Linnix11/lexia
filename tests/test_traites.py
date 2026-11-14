"""Import des traités européens et internationaux (ingest/sources/traites.py)."""

import pytest

from api.textes import codes_cites
from ingest.sources import traites

UE = """<html><body><div>
<p class="doc-ti">TRAITÉ SUR L'UNION EUROPÉENNE (VERSION CONSOLIDÉE)</p>
<p class="normal">PRÉAMBULE</p>
<p class="normal">RÉSOLUS à franchir une nouvelle étape dans le processus d'intégration européenne,</p>
<p class="ti-section-1">TITRE I</p>
<p class="ti-section-2"><span class="bold">DISPOSITIONS COMMUNES</span></p>
<div id="001">
  <p class="ti-art">Article premier</p>
  <p class="sti-art"><span>(ex-article premier TUE)</span> <a href="#ntr2-x">(<span class="super note-tag">2</span>)</a></p>
  <p class="normal">Par le présent traité, les HAUTES PARTIES CONTRACTANTES instituent entre elles une UNION EUROPÉENNE.</p>
</div>
<div id="002">
  <p class="ti-art">Article 2</p>
  <p class="sti-art">Dignité humaine</p>
  <div>1.\xa0\xa0\xa0L'Union est fondée sur les valeurs de respect de la dignité humaine.</div>
  <table><tr><td><p class="normal">a)</p></td><td><p class="normal">premier point;</p></td></tr></table>
</div>
<p class="doc-ti">PROTOCOLES</p>
<div id="p01"><p class="ti-art">Article 99</p><p class="normal">Un protocole : jamais repris.</p></div>
</div></body></html>""".replace("\\xa0", "\xa0")

CEDH = """Convention européenne des droits de l’homme
Table des matières ................................ 3
ARTICLE 1
Obligation de respecter les droits de l’homme
Les Hautes Parties contractantes reconnaissent à toute personne
relevant de leur juridiction les droits et libertés définis au titre I.
TITRE I
DROITS ET LIBERTÉS
ARTICLE 2
Droit à la vie
1. L e droit de toute personne à la vie est protégé par la loi. La
mort ne peut être infligée à quiconque intentionnellement.
34 35
2. La mort n’est pas considérée comme infligée en violation de cet
article dans les cas où elle résulterait d’un recours à la force :
a) pour assurer la défense de toute personne contre la violence illégale ;
Fait à Rome, le 4 novembre 1950, en français et en anglais.
Protocole additionnel
à la Convention de sauvegarde
des droits de l’homme
Sont convenus de ce qui suit :
ARTICLE 1
Protection de la propriété
Toute personne physique ou morale a droit au respect de ses
biens.
Protocole n° 12
à la Convention de sauvegarde
ARTICLE 1
Interdiction générale de la discrimination
Non ratifié par la France : ne doit pas être repris.
"""

ONU = """<html><body>
<p>Note sur les amendements : à ignorer.</p>
<h2>Préambule</h2>
<h3>NOUS, PEUPLES DES NATIONS UNIES, RÉSOLUS</h3>
<p>à préserver les générations futures du fléau de la guerre,</p>
<h2>Chapitre I: Buts et principes</h2>
<h3>Article 1</h3>
<p>Les buts des Nations Unies sont les suivants :</p>
<ol class="ol-decimal"><li>Maintenir la paix et la sécurité internationales;</li><li>Développer des relations amicales.</li></ol>
<h3>Article 2</h3>
<p>L'Organisation est fondée sur le principe de l'égalité souveraine de tous ses Membres.</p>
<h2>Ressources</h2>
<p>Pied de page : à ignorer.</p>
</body></html>"""


def source(classe, sid, **kw):
    return classe(sid, "Texte d'essai", "https://exemple.fr/texte", "https://exemple.fr/brut", "version d'essai",
                  kw.pop("depuis", "2009-12-01"), min_articles=kw.pop("min_articles", 1))


def test_traite_ue_articles_notes_ancien_numero_et_protocoles_exclus():
    ps = source(traites.TraiteUE, "tue").parse(UE)
    pre, a1, a2 = ps
    assert pre.type == "preambule" and pre.alineas == ["RÉSOLUS à franchir une nouvelle étape dans le processus "
                                                        "d'intégration européenne,"]
    assert (a1.numero, a1.titre, a1.meta["ancien_numero"]) == ("1", None, "ex-article premier TUE")
    assert "(2)" not in a1.entete and "2" not in (a1.meta["ancien_numero"])  # appel de note retire
    assert a1.meta["plan"] == ["TITRE I", "DISPOSITIONS COMMUNES"] and a1.meta["en_vigueur"] is True
    assert a1.entete == "Texte d'essai, article 1 (en vigueur, depuis le 1er décembre 2009)"
    assert a2.titre == "Dignité humaine"     # Charte : intitule de l'article
    assert a2.alineas == ["1. L'Union est fondée sur les valeurs de respect de la dignité humaine.", "a) premier point;"]
    assert [p.numero for p in ps] == [None, "1", "2"]   # l'article 99 du protocole n'est pas repris


def test_cedh_titres_alineas_lettrine_pages_et_protocoles():
    ps = source(traites.ConventionEDH, "cedh", depuis="1974-05-03").parse(CEDH)
    assert [p.numero for p in ps] == ["1", "2", "P1-1"]      # protocole 12 exclu
    a1, a2, p1 = ps
    assert a1.titre == "Obligation de respecter les droits de l’homme"
    assert a1.alineas == ["Les Hautes Parties contractantes reconnaissent à toute personne relevant de leur "
                          "juridiction les droits et libertés définis au titre I."]
    assert a2.meta["plan"] == ["TITRE I", "DROITS ET LIBERTÉS"]
    assert a2.alineas[0].startswith("1. Le droit de toute personne")     # lettrine « L e » recollee
    assert len(a2.alineas) == 3 and a2.alineas[2].startswith("a) pour assurer")
    assert "34 35" not in " ".join(a2.alineas) and "Fait à Rome" not in " ".join(a2.alineas)
    assert p1.titre == "Protection de la propriété" and p1.alineas == ["Toute personne physique ou morale a droit au "
                                                                       "respect de ses biens."]
    # Un protocole n'a pas de date d'entree en vigueur verifiee pour la France : elle n'est pas affichee.
    assert p1.entete.endswith("Protocole additionnel, article 1 - Protection de la propriété (en vigueur)")
    assert p1.meta["date_debut"] is None and a1.meta["date_debut"] == "1974-05-03"
    assert p1.id == "cedh:p1:art:1"


def test_charte_onu_preambule_articles_et_listes():
    ps = source(traites.CharteONU, "charte_onu", depuis="1945-10-24").parse(ONU)
    pre, a1, a2 = ps
    assert pre.alineas == ["NOUS, PEUPLES DES NATIONS UNIES, RÉSOLUS", "à préserver les générations futures du fléau "
                                                                         "de la guerre,"]
    assert a1.alineas == ["Les buts des Nations Unies sont les suivants :", "1. Maintenir la paix et la sécurité "
                          "internationales;", "2. Développer des relations amicales."]
    assert a1.meta["plan"] == ["Chapitre I: Buts et principes"]
    assert a2.alineas == ["L'Organisation est fondée sur le principe de l'égalité souveraine de tous ses Membres."]
    assert "Pied de page" not in " ".join(a for p in ps for a in p.alineas)


def test_texte_incomplet_refuse():
    with pytest.raises(traites.ParseError):
        source(traites.TraiteUE, "tue", min_articles=50).parse(UE)
    with pytest.raises(traites.ParseError):
        source(traites.CharteONU, "charte_onu").parse("<html><h2>Autre chose</h2></html>")


def test_sources_declarees_dans_le_registre():
    from api.matieres import sources_par_matiere
    s = sources_par_matiere()
    assert {"tue", "tfue", "charte_droits_fondamentaux_ue", "cedh"} <= set(s["droit_europeen"])
    assert {"charte_onu", "cedh"} <= set(s["droit_international"])
    assert {t.SOURCE_ID for t in traites.SOURCES} == {"tue", "tfue", "charte_droits_fondamentaux_ue", "cedh",
                                                      "charte_onu"}


@pytest.mark.parametrize("question, attendu", [
    ("Paul tue Jean : que dit l'article 221-1 du code pénal ?", ("code_penal",)),   # le verbe, pas le traité
    ("Paul tue Jean, est-ce un meurtre ?", ()),
    ("Que dit l'article 6 du TUE ?", ("tue",)),
    ("L'article 101 TFUE et les ententes", ("tfue",)),
    ("article 8 de la CEDH", ("cedh",)),
    ("article 47 de la Charte des droits fondamentaux", ("charte_droits_fondamentaux_ue",)),
    ("article 51 de la Charte des Nations unies", ("charte_onu",)),
    ("article 7 de la Charte de l'environnement", ()),
])
def test_traites_reconnus_dans_les_questions(question, attendu):
    assert codes_cites(question) == attendu
