"""Ajoute les deux graphiques natifs de pitch.pptx avec python-pptx (Keynote n'affiche pas ceux de pptxgenjs).

Lancer apres generer_pitch.js : python3 docs/business/outils/ajouter_graphiques.py
Valeurs : feuille Synthese de projections.xlsx et analyse de sensibilite du business plan (partie 10).
"""
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

DECK = Path(__file__).resolve().parent.parent / "pitch.pptx"
VERT, GRIS, BRONZE, BRIQUE, TEXTE = "2F5D4A", "5B6B63", "B8873B", "B5543A", "1E2B25"


def styler(chart, titre):
    chart.font.name = "Calibri"
    chart.font.size = Pt(10)
    chart.font.color.rgb = RGBColor.from_string(TEXTE)
    chart.has_title = True
    chart.chart_title.text_frame.text = titre
    p = chart.chart_title.text_frame.paragraphs[0]
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.name = "Calibri"
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor.from_string("E3E6E2")
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(9)
    va.tick_labels.font.color.rgb = RGBColor.from_string(GRIS)
    va.tick_labels.number_format = "0"
    va.tick_labels.number_format_is_linked = False
    ca = chart.category_axis
    ca.tick_labels.font.size = Pt(10)
    ca.tick_labels.font.color.rgb = RGBColor.from_string(GRIS)
    ca.format.line.color.rgb = RGBColor.from_string("C9CFCA")


def etiquettes(serie, taille=9):
    serie.data_labels.show_value = True
    serie.data_labels.number_format = "0.0"
    serie.data_labels.number_format_is_linked = False
    serie.data_labels.font.size = Pt(taille)
    serie.data_labels.font.color.rgb = RGBColor.from_string(TEXTE)
    serie.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END


prs = Presentation(DECK)

# Diapositive 9 : chiffre d'affaires par annee et par scenario
s9 = prs.slides[8]
cd = CategoryChartData()
cd.categories = ["2027", "2028", "2029"]
cd.add_series("Prudent", (0.3, 1.1, 1.5))
cd.add_series("Central", (2.9, 11.2, 19.2))
cd.add_series("Ambitieux", (15.4, 67.3, 132.8))
gf = s9.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(1.15), Inches(5.25), Inches(3.65), cd)
gf.name = "graphique chiffre affaires"
ch = gf.chart
styler(ch, "Chiffre d'affaires hors TVA (k€)")
ch.has_legend = True
ch.legend.position = XL_LEGEND_POSITION.BOTTOM
ch.legend.include_in_layout = False
ch.legend.font.size = Pt(10)
for serie, coul in zip(ch.series, (GRIS, VERT, BRONZE)):
    serie.format.fill.solid()
    serie.format.fill.fore_color.rgb = RGBColor.from_string(coul)
    etiquettes(serie)
ch.plots[0].gap_width = 60
ch.plots[0].overlap = 0

# Diapositive 12 : sensibilite du scenario central
s12 = prs.slides[11]
cd = CategoryChartData()
cats = ["Central tel quel", "Perte abonnés 7 %/mois", "Gratuit 25 q/mois", "Conversion 2 %/mois", "Sans publicité",
        "Conv. 2 % + gratuit 25 q + sans pub"]
vals = (-18.4, -15.2, -13.2, -6.2, 1.1, 15.3)
cd.categories = cats
cd.add_series("Résultat cumulé sur 36 mois (k€)", vals)
gf = s12.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(4.45), Inches(1.27), Inches(4.95), Inches(3.6), cd)
gf.name = "graphique sensibilite"
ch = gf.chart
styler(ch, "Scénario central : résultat cumulé sur 36 mois (k€)")
ch.has_legend = False
ch.category_axis.tick_labels.font.size = Pt(9)
ch.category_axis.reverse_order = True
from pptx.enum.chart import XL_TICK_LABEL_POSITION
ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
serie = ch.series[0]
serie.invert_if_negative = False
etiquettes(serie)
for i, v in enumerate(vals):
    pt = serie.points[i]
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = RGBColor.from_string(BRIQUE if v < 0 else VERT)
ch.plots[0].gap_width = 50
ch.value_axis.minimum_scale = -25
ch.value_axis.maximum_scale = 20
ch.value_axis.major_unit = 5

prs.save(DECK)
print(DECK)
