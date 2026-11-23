// Genere docs/business/pitch.pptx (pitch deck de Lexia, 12 diapositives).
// Lancer : NODE_PATH=<dossier contenant pptxgenjs> node docs/business/outils/generer_pitch.js [chemin de apply_theme.js]
const path = require("path");
const pptxgen = require("pptxgenjs");

const ICI = __dirname;
const SORTIE = path.join(ICI, "..", "pitch.pptx");
const CAPTURES = path.join(ICI, "..", "captures");

const THEME = {
  name: "Lexia",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1E2B25", lt1: "FFFFFF", dk2: "2F5D4A", lt2: "F2F4F1",
    accent1: "2F5D4A", accent2: "B8873B", accent3: "7FA58F", accent4: "B5543A",
    accent5: "DCE7E0", accent6: "5B6B63", hlink: "2F5D4A", folHlink: "5B6B63",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 pouces
pres.title = "Lexia, business plan";
pres.author = "Axion Studio";
pres.company = "Axion Studio";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// Mises en page -------------------------------------------------------------------------------
pres.defineSlideMaster({
  title: "TITRE",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.55, w: 8.6, h: 1.2, fontSize: 48, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 2.85, w: 8.6, h: 1.6, fontSize: 18, color: C.accent5, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENU",
  background: { color: C.background1 },
  margin: [0.5, 0.5, 0.5, 0.5],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75, fontSize: 28, bold: true, color: C.text2, fontFace: THEME.headFontFace, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "Lexia, business plan, 23 novembre 2026. Outil de planification, pas un conseil financier.", options: { x: 0.5, y: 5.25, w: 7.6, h: 0.25, fontSize: 8, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 9.1, y: 5.25, w: 0.4, h: 0.25, fontSize: 8, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "FIN",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75, fontSize: 28, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "Lexia, business plan, 23 novembre 2026. Outil de planification, pas un conseil financier.", options: { x: 0.5, y: 5.25, w: 7.6, h: 0.25, fontSize: 8, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 9.1, y: 5.25, w: 0.4, h: 0.25, fontSize: 8, color: C.accent5, align: "right" },
});

// Outils de composition ----------------------------------------------------------------------
const ombre = () => ({ type: "outer", color: "1E2B25", opacity: 0.12, blur: 6, offset: 2, angle: 90 });

function carte(slide, x, y, w, h, nom, fond) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fond || C.background2 }, line: { type: "none" }, shadow: ombre(), objectName: nom });
}
function pastille(slide, x, y, texte, nom, couleur) {
  slide.addShape(pres.ShapeType.ellipse, { x, y, w: 0.42, h: 0.42, fill: { color: couleur || C.accent1 }, line: { type: "none" }, objectName: nom });
  slide.addText(texte, { x, y, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: nom + " texte" });
}
function texte(slide, t, o) {
  slide.addText(t, Object.assign({ fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true }, o));
}
function chiffre(slide, x, y, w, grand, petit, nom, couleur) {
  texte(slide, grand, { x, y, w, h: 0.62, fontSize: 32, bold: true, color: couleur || C.accent1, fontFace: THEME.headFontFace, objectName: nom });
  texte(slide, petit, { x, y: y + 0.62, w, h: 0.5, fontSize: 11, color: C.accent6, objectName: nom + " legende" });
}
const axes = {
  catAxisLabelColor: HEX.accent6, valAxisLabelColor: HEX.accent6, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 10, valAxisLabelFontSize: 9, valGridLine: { color: "E3E6E2", size: 0.5 }, catGridLine: { style: "none" },
  dataLabelFontFace: "+mn-lt", dataLabelFontSize: 9, dataLabelColor: HEX.dk1, titleFontFace: "+mn-lt", legendFontFace: "+mn-lt",
  legendFontSize: 10, legendColor: HEX.dk1, titleColor: HEX.dk1, titleFontSize: 12,
};

// 1. Titre -----------------------------------------------------------------------------------
pres.addSection({ title: "Ouverture" });
let s = pres.addSlide({ masterName: "TITRE", sectionTitle: "Ouverture" });
s.addText("Lexia", { placeholder: "title" });
s.addText([
  { text: "Comprendre le droit, sources à l'appui.", options: { breakLine: true } },
  { text: "Assistant d'étude pour les étudiants de licence en droit", options: { breakLine: true, fontSize: 14 } },
  { text: "Business plan, 23 novembre 2026, Axion Studio", options: { fontSize: 12 } },
], { placeholder: "body" });
s.addShape(pres.ShapeType.roundRect, { x: 0.7, y: 0.7, w: 0.42, h: 0.62, rectRadius: 0.04, fill: { color: C.background1 }, line: { type: "none" }, objectName: "marque page" });
s.addText("L", { x: 0.7, y: 0.7, w: 0.42, h: 0.62, fontSize: 22, bold: true, color: C.text2, align: "center", valign: "middle", fontFace: THEME.headFontFace, margin: 0, isTextBox: true, objectName: "marque page lettre" });
s.addNotes("Lexia répond aux questions de droit des étudiants de licence à partir des textes et décisions officiels, et cite chaque source. Ce document est un outil de planification : les projections reposent sur des hypothèses non encore mesurées.");

// 2. Problème --------------------------------------------------------------------------------
pres.addSection({ title: "Problème et solution" });
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Problème et solution" });
s.addText("Réviser le droit avec des sources sûres reste difficile", { placeholder: "title" });
const pb = [
  ["Des supports qui vieillissent", "Un polycopié peut encore citer 1134 ou 1382, numéros d'avant la réforme de 2016."],
  ["Des IA qui ne prouvent pas", "Un assistant général peut inventer un article (hypothèse de départ, non mesurée ici)."],
  ["Une méthode exigeante", "Cas pratique, commentaire, dissertation : des plans attendus, peu de retours individuels."],
  ["Des sources brutes", "Légifrance contient tout, encore faut-il savoir quoi chercher en L1."],
];
pb.forEach(([t, d], i) => {
  const x = 0.5 + (i % 2) * 4.6, y = 1.3 + Math.floor(i / 2) * 1.85;
  carte(s, x, y, 4.4, 1.65, `probleme ${i + 1}`);
  pastille(s, x + 0.25, y + 0.28, String(i + 1), `probleme ${i + 1} numero`);
  texte(s, t, { x: x + 0.85, y: y + 0.28, w: 3.35, h: 0.42, fontSize: 16, bold: true, color: C.text2, valign: "middle", objectName: `probleme ${i + 1} titre` });
  texte(s, d, { x: x + 0.85, y: y + 0.78, w: 3.35, h: 0.75, fontSize: 13, objectName: `probleme ${i + 1} texte` });
});
s.addNotes("Quatre constats. Le deuxième est l'hypothèse de départ du produit : il n'a pas été mesuré sur les outils concurrents dans ce business plan.");

// 3. Solution --------------------------------------------------------------------------------
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Problème et solution" });
s.addText("Lexia répond à partir du droit en vigueur et le prouve", { placeholder: "title" });
carte(s, 0.5, 1.25, 3.0, 3.75, "chiffres du produit", C.accent5);
chiffre(s, 0.8, 1.45, 2.5, "916 000", "passages officiels : codes, lois, Constitution, jurisprudence", "chiffre corpus");
chiffre(s, 0.8, 2.6, 2.5, "20", "matières de la L1 à la L3", "chiffre matieres");
chiffre(s, 0.8, 3.75, 2.5, "5", "modes : expliquer, fiche, cas pratique, commentaire, dissertation", "chiffre modes");
const sol = [
  ["Citations contrôlées par le serveur", "Une affirmation de droit sans source est retirée ; sinon Lexia s'abstient."],
  ["Version en vigueur en un clic", "Codes et lois mis à jour chaque nuit ; anciens numéros reliés aux actuels."],
  ["Méthodes de la licence", "Rubriques imposées par mode, niveau adapté au semestre."],
  ["Révision et cours", "Questionnaires, cartes à retourner, résumés vocaux, cartes mentales, cours déposés."],
];
sol.forEach(([t, d], i) => {
  const y = 1.3 + i * 0.93;
  pastille(s, 3.9, y, String(i + 1), `solution ${i + 1} numero`);
  texte(s, t, { x: 4.5, y: y - 0.04, w: 5.0, h: 0.35, fontSize: 15, bold: true, color: C.text2, objectName: `solution ${i + 1} titre` });
  texte(s, d, { x: 4.5, y: y + 0.32, w: 5.0, h: 0.5, fontSize: 12, objectName: `solution ${i + 1} texte` });
});
s.addNotes("Décisions D22, D53, D66, D78, D89, D104, D106, D112. Qualité : 187 questions de cours sur 187 retrouvées sur les jeux internes ; notation par un enseignant pas encore faite.");

// 4. Démo ------------------------------------------------------------------------------------
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Problème et solution" });
s.addText("Démonstration : le site en ligne", { placeholder: "title" });
s.addImage({ path: path.join(CAPTURES, "accueil.png"), x: 0.5, y: 1.2, w: 5.6, h: 3.5, objectName: "capture accueil", altText: "Page d'accueil de Lexia avec un exemple de réponse sur la responsabilité pour faute, citant les articles 1240 et 1241 du Code civil" });
s.addImage({ path: path.join(CAPTURES, "tarifs.png"), x: 6.35, y: 1.2, w: 3.15, h: 1.97, objectName: "capture tarifs", altText: "Page Tarifs : Gratuit 0 euro, Étudiant 4,99 euros par mois, Intensif 9,99 euros par mois" });
texte(s, "Captures du 23 novembre 2026, https://lexia-axionstudio.cloud. À gauche, l'accueil avec un exemple de réponse : l'essentiel, un exemple, les articles cités et leur date d'entrée en vigueur. À droite, les trois formules.", { x: 6.35, y: 3.35, w: 3.15, h: 1.35, fontSize: 11, color: C.accent6, objectName: "legende demo" });
s.addNotes("Captures prises le 23 novembre 2026 sur le site public. L'espace étudiant (questions, questionnaires, fiches) demande un compte et n'est pas capturé ici.");

// 5. Marché ----------------------------------------------------------------------------------
pres.addSection({ title: "Marché et modèle" });
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Marché et modèle" });
s.addText("141 600 étudiants en licence de droit", { placeholder: "title" });
const marche = [
  ["TAM", "7,6 M€ par an", "141 600 étudiants × 5,99 € × 9 mois", 9.0, C.text2],
  ["SAM", "1,9 M€ par an", "25 % prêts à payer un outil spécialisé (hypothèse non sourcée)", 6.4, C.accent1],
  ["SOM", "19 k€ à 133 k€", "CA de l'année 3 : scénario central (1 % du SAM) et ambitieux (7 %)", 3.6, C.accent2],
];
marche.forEach(([k, v, d, w, coul], i) => {
  const y = 1.3 + i * 1.12;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y, w, h: 0.95, rectRadius: 0.08, fill: { color: coul }, line: { type: "none" }, objectName: `barre ${k}` });
  texte(s, k, { x: 0.7, y, w: 0.8, h: 0.95, fontSize: 18, bold: true, color: C.background1, valign: "middle", objectName: `barre ${k} sigle` });
  texte(s, v, { x: 1.5, y: y + 0.1, w: 2.2, h: 0.4, fontSize: 18, bold: true, color: C.background1, fontFace: THEME.headFontFace, objectName: `barre ${k} valeur` });
  texte(s, d, { x: 1.5, y: y + 0.5, w: Math.max(w - 1.2, 2.0), h: 0.4, fontSize: 11, color: C.background1, objectName: `barre ${k} calcul` });
});
texte(s, "Licence de droit, universités, 2025-2026, observé : note Flash du SIES n° 25 (octobre 2026). 5,99 € = recette moyenne avec 20 % d'Intensif (hypothèse). Extensions non chiffrées : master (82 700), capacité, établissements privés.", { x: 4.4, y: 3.6, w: 5.1, h: 1.1, fontSize: 11, color: C.accent6, objectName: "sources marche" });
s.addNotes("TAM : 141 600 × 5,99 × 9 = 7,63 M€. SAM : 35 400 étudiants × 5,99 × 9 = 1,91 M€. SOM : chiffre d'affaires de l'année 3 des projections. Le taux de 25 % n'a pas de source : il doit être remplacé par une enquête ou par la conversion mesurée.");

// 6. Modèle économique -----------------------------------------------------------------------
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Marché et modèle" });
s.addText("Freemium : 0 €, 4,99 € et 9,99 € par mois", { placeholder: "title" });
const formules = [
  ["Gratuit", "0 €", "10 questions et 2 questionnaires par jour, 3 cours"],
  ["Étudiant", "4,99 €", "100 questions et 20 questionnaires par jour, 30 cours"],
  ["Intensif", "9,99 €", "300 questions et 100 questionnaires par jour, 100 cours"],
];
formules.forEach(([n, p, d], i) => {
  const x = 0.5 + i * 3.05;
  carte(s, x, 1.25, 2.85, 1.85, `formule ${n}`, i === 1 ? C.accent5 : C.background2);
  texte(s, n, { x: x + 0.25, y: 1.4, w: 2.4, h: 0.35, fontSize: 15, bold: true, color: C.text2, objectName: `formule ${n} nom` });
  texte(s, p, { x: x + 0.25, y: 1.75, w: 2.4, h: 0.55, fontSize: 28, bold: true, color: C.text1, fontFace: THEME.headFontFace, objectName: `formule ${n} prix` });
  texte(s, d, { x: x + 0.25, y: 2.35, w: 2.4, h: 0.65, fontSize: 11, color: C.accent6, objectName: `formule ${n} quotas` });
});
chiffre(s, 0.5, 3.35, 2.9, "0,0028 €", "coût mesuré d'une question (essais, grille payante de Gemini)", "chiffre cout question", C.accent2);
chiffre(s, 3.55, 3.35, 2.9, "4,18 €", "marge brute mensuelle d'un abonné Étudiant (220 questions, hypothèse)", "chiffre marge etudiant", C.accent2);
chiffre(s, 6.6, 3.35, 2.9, "33", "comptes gratuits actifs dont un abonné Étudiant couvre le coût du modèle", "chiffre gratuits couverts", C.accent2);
texte(s, "Paiement unique de 1 à 12 mois par Stripe (1,5 % + 0,25 €), sans reconduction. Micro-entreprise en franchise de TVA.", { x: 0.5, y: 4.62, w: 9.0, h: 0.4, fontSize: 11, color: C.accent6, objectName: "note paiement" });
s.addNotes("Coût par question : 2 036 jetons d'entrée et 538 de sortie par réponse (logs/modele.jsonl, 20 appels d'essai), 0,30 et 2,50 $ par million, 5 % de secours Gemini 3.8 Flash et 5 % Groq (hypothèses), +25 % d'appels annexes, 1,0968 $ pour 1 €. Un abonné qui épuise son quota chaque jour coûte plus qu'il ne rapporte : seuil d'environ 57 questions par jour pour l'Étudiant.");

// 7. Traction --------------------------------------------------------------------------------
pres.addSection({ title: "Traction et concurrence" });
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Traction et concurrence" });
s.addText("Traction : produit construit, vente pas encore ouverte", { placeholder: "title" });
carte(s, 0.5, 1.25, 4.35, 3.75, "colonne fait");
texte(s, "Fait", { x: 0.75, y: 1.4, w: 3.9, h: 0.4, fontSize: 16, bold: true, color: C.text2, objectName: "titre fait" });
texte(s, [
  { text: "Site complet en ligne : comptes, formules, pages légales", options: { bullet: true, breakLine: true } },
  { text: "Corpus officiel mis à jour chaque nuit", options: { bullet: true, breakLine: true } },
  { text: "Paiement Stripe et rétractation en ligne codés", options: { bullet: true, breakLine: true } },
  { text: "Trois audits (sécurité, site, juridique) et corrections", options: { bullet: true, breakLine: true } },
  { text: "114 décisions documentées", options: { bullet: true } },
], { x: 0.75, y: 1.85, w: 3.9, h: 3.0, fontSize: 13, paraSpaceAfter: 6, objectName: "liste fait" });
carte(s, 5.15, 1.25, 4.35, 3.75, "colonne pas encore", "F7EDE9");
texte(s, "Pas encore", { x: 5.4, y: 1.4, w: 3.9, h: 0.4, fontSize: 16, bold: true, color: C.accent4, objectName: "titre pas encore" });
texte(s, [
  { text: "0 abonné payant, 0 € de chiffre d'affaires", options: { bullet: true, breakLine: true } },
  { text: "Paiement en ligne inactif, API Gemini au niveau gratuit", options: { bullet: true, breakLine: true } },
  { text: "SIRET en cours, aucun médiateur désigné", options: { bullet: true, breakLine: true } },
  { text: "Réponses non notées par un enseignant", options: { bullet: true, breakLine: true } },
  { text: "Nom « Lexia » non validé par un conseil", options: { bullet: true } },
], { x: 5.4, y: 1.85, w: 3.9, h: 3.0, fontSize: 13, paraSpaceAfter: 6, objectName: "liste pas encore" });
s.addNotes("État vérifié le 23 novembre 2026 sur /api/config (paiement: false, gemini_payant: false, médiateur absent, SIRET en cours d'attribution). Aucun chiffre d'inscriptions n'est donné : la base des comptes n'a pas été lue pour ce document.");

// 8. Concurrence -----------------------------------------------------------------------------
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Traction et concurrence" });
s.addText("Spécialisé face à un outil général gratuit", { placeholder: "title" });
const tete = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 12, valign: "middle" } });
const cel = (t, o) => ({ text: t, options: Object.assign({ fontSize: 11, valign: "middle", color: HEX.dk1 }, o || {}) });
const plus = { color: HEX.dk2, bold: true };
const moins = { color: HEX.accent4 };
const lignes = [
  [tete("Critère"), tete("Lexia"), tete("Gemini Notebook"), tete("Légifrance")],
  [cel("Corpus juridique officiel déjà chargé"), cel("Oui, environ 916 000 passages", plus), cel("Non : documents apportés", moins), cel("Oui, à chercher soi-même")],
  [cel("Règle prouvée par une citation contrôlée"), cel("Oui, contrôle serveur", plus), cel("Cite les documents fournis"), cel("Sans objet")],
  [cel("Version en vigueur en un clic"), cel("Oui", plus), cel("Non", moins), cel("Oui")],
  [cel("Méthodes de la licence"), cel("Oui, 5 modes", plus), cel("Non spécialisé", moins), cel("Non", moins)],
  [cel("Révision multimédia"), cel("Cartes, résumés vocaux, cartes mentales"), cel("Très riche : audio, vidéo, cartes", plus), cel("Non", moins)],
  [cel("Prix pour l'étudiant"), cel("0 à 9,99 € par mois"), cel("Gratuit ; AI Plus offert 12 mois aux majeurs (jusqu'au 31/12/2026)", plus), cel("Gratuit", plus)],
  [cel("Mobile"), cel("Site installable, app iOS non publiée", moins), cel("Apps iOS et Android", plus), cel("Site")],
];
s.addTable(lignes, { x: 0.5, y: 1.2, w: 9.0, colW: [2.6, 2.2, 2.4, 1.8], rowH: 0.42, border: { type: "solid", pt: 0.5, color: "D5DAD6" }, fill: { color: HEX.lt1 }, fontFace: THEME.bodyFontFace, margin: 0.05, objectName: "tableau concurrence" });
texte(s, "Comparatif du 19 novembre 2026 (pages Google officielles). Assistants d'IA généralistes non comparés ici. Aucune publicité comparative nommée (C. consom. L. 122-1).", { x: 0.5, y: 4.75, w: 9.0, h: 0.4, fontSize: 10, color: C.accent6, objectName: "source concurrence" });
s.addNotes("Lexia ne gagne ni sur le prix, ni sur la révision multimédia, ni sur le mobile. Ses atouts : droit positif sans rien préparer, citations qui prouvent la règle, version en vigueur, méthodes. L'offre étudiante de Google pèse sur la conversion au moins jusqu'à fin 2027.");

// 9. Projections -----------------------------------------------------------------------------
pres.addSection({ title: "Chiffres" });
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Chiffres" });
s.addText("Projections sur 3 ans : trois scénarios", { placeholder: "title" });
// Graphique ajouté par ajouter_graphiques.py (Keynote n'affiche pas les graphiques de pptxgenjs).
const proj = [
  ["Résultat cumulé sur 36 mois", "−15,9 k€", "−18,0 k€", "+31,1 k€"],
  ["Abonnés en fin d'année 3", "24", "325", "2 781"],
  ["Point mort", "non atteint", "juil. 2028", "avr. 2027"],
  ["LTV / CAC, année 3", "négatif", "1,1", "4,5"],
];
const tete10 = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 10, valign: "middle" } });
const tp = [[tete10(""), tete10("Prudent"), tete10("Central"), tete10("Ambitieux")]].concat(proj.map(r => [cel(r[0], { fontSize: 10 }), cel(r[1], { fontSize: 10 }), cel(r[2], { fontSize: 10, bold: true }), cel(r[3], { fontSize: 10 })]));
s.addTable(tp, { x: 5.95, y: 1.2, w: 3.55, colW: [1.25, 0.75, 0.75, 0.8], rowH: 0.48, border: { type: "solid", pt: 0.5, color: "D5DAD6" }, fill: { color: HEX.lt1 }, fontFace: THEME.bodyFontFace, margin: 0.04, objectName: "tableau projections" });
texte(s, "Avant rémunération de l'éditeur. Hypothèses d'acquisition, de conversion et de rachat non mesurées : projections.xlsx, feuille Hypothèses.", { x: 5.95, y: 3.75, w: 3.55, h: 1.0, fontSize: 10, color: C.accent6, objectName: "note projections" });
s.addNotes("Conversion mensuelle des gratuits actifs : 0,6 %, 1,2 %, 2 %. Perte mensuelle des abonnés : 15 %, 10 %, 7 %, plus 15 à 25 points en été. Le scénario ambitieux perd la franchise de TVA en 2028 et dépasse le plafond micro en 2029. Le point mort central de juillet 2028 n'est pas durable.");

// 10. Feuille de route -----------------------------------------------------------------------
pres.addSection({ title: "Plan" });
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Plan" });
s.addText("Feuille de route sur 12 mois", { placeholder: "title" });
const route = [
  ["Déc. 2026", "Prérequis", "Gemini payant, âge 15 ou 18 ans, SIRET, médiateur, avis sur le nom"],
  ["Janv. 2027", "Ouverture de la vente", "Stripe en réel, avocat (CGU, D77), appel aux enseignants"],
  ["Févr.-mars", "Mesurer", "Conversion et rachat sur 8 semaines, dépôt de marque si avis favorable"],
  ["Avr.-mai", "Tester", "Coût réel par question ; publicité 150 à 300 € si CAC < LTV / 2"],
  ["Juin-août", "Préparer la rentrée", "App iOS, synchronisation, offre étudiante de Google à revérifier"],
  ["Sept.-nov.", "Rentrée 2027", "Palier publicitaire 2 si justifié, statut et prix revus"],
];
s.addShape(pres.ShapeType.line, { x: 0.75, y: 1.62, w: 8.5, h: 0, line: { color: HEX.accent3, width: 2 }, objectName: "frise" });
route.forEach(([q, t, d], i) => {
  const x = 0.5 + i * 1.52;
  pastille(s, x + 0.05, 1.41, String(i + 1), `etape ${i + 1}`, i < 2 ? C.accent2 : C.accent1);
  texte(s, q, { x, y: 1.98, w: 1.42, h: 0.3, fontSize: 12, bold: true, color: C.text2, objectName: `etape ${i + 1} date` });
  texte(s, t, { x, y: 2.3, w: 1.42, h: 0.55, fontSize: 13, bold: true, objectName: `etape ${i + 1} titre` });
  texte(s, d, { x, y: 2.88, w: 1.42, h: 1.35, fontSize: 11, color: C.accent6, objectName: `etape ${i + 1} detail` });
});
carte(s, 0.5, 4.35, 9.0, 0.6, "regle de passage", C.accent5);
texte(s, "Règle de passage : aucun palier publicitaire tant que la conversion, le rachat et le coût par abonné ne sont pas mesurés.", { x: 0.75, y: 4.35, w: 8.5, h: 0.6, fontSize: 13, bold: true, color: C.text2, valign: "middle", objectName: "regle de passage texte" });
s.addNotes("Chaque palier commercial dépend d'une mesure : pas de publicité avant d'avoir mesuré la conversion et le rachat, pas de dépôt de marque avant l'avis d'un conseil.");

// 11. Risques --------------------------------------------------------------------------------
s = pres.addSlide({ masterName: "CONTENU", sectionTitle: "Plan" });
s.addText("Cinq risques à traiter avant de grandir", { placeholder: "title" });
const risques = [
  ["Conditions de Gemini", "18 ans minimum et niveau payant obligatoire dans l'EEE ; Lexia accepte dès 15 ans", "Trancher l'âge ou changer de fournisseur ; activer la facturation"],
  ["Marque", "« LEXIA » déjà enregistrée pour des logiciels éducatifs (UE) et des services juridiques (France)", "Avis d'un conseil avant toute dépense de visibilité, nom de repli"],
  ["Fiabilité", "Erreur de droit possible ; jurisprudence en retard de 2 à 3 mois", "Contrôle des citations, abstention, notation par un enseignant"],
  ["Consultation juridique (D77)", "Faits personnels expliqués dans un service payant", "Avis d'un avocat ; faits reformulés en exercice si besoin"],
  ["Concurrence gratuite", "AI Plus offert aux étudiants majeurs jusqu'à fin 2026", "Positionnement spécialisé, conversion mesurée avant la publicité"],
];
risques.forEach(([t, r, m], i) => {
  const y = 1.2 + i * 0.78;
  carte(s, 0.5, y, 9.0, 0.68, `risque ${i + 1}`);
  texte(s, t, { x: 0.7, y, w: 2.1, h: 0.68, fontSize: 13, bold: true, color: C.accent4, valign: "middle", objectName: `risque ${i + 1} titre` });
  texte(s, r, { x: 2.9, y, w: 3.4, h: 0.68, fontSize: 11, valign: "middle", objectName: `risque ${i + 1} constat` });
  texte(s, m, { x: 6.45, y, w: 2.9, h: 0.68, fontSize: 11, color: C.text2, valign: "middle", objectName: `risque ${i + 1} reponse` });
});
s.addNotes("Sources : docs/note-editeur-2026-11-20.md (âge, médiateur, D77), docs/marque-lexia.md (EUIPO 015377401, OMPI 1647070, INPI 4010966), docs/comparatif-notebooklm.md. Aucune conclusion juridique : avis d'un avocat et d'un conseil en propriété industrielle à demander.");

// 12. Besoin de financement ------------------------------------------------------------------
s = pres.addSlide({ masterName: "FIN", sectionTitle: "Plan" });
s.addText("Besoin de financement : 3 à 18 k€ selon la publicité", { placeholder: "title" });
texte(s, "3 à 4 k€", { x: 0.5, y: 1.25, w: 3.6, h: 0.75, fontSize: 40, bold: true, color: C.background1, fontFace: THEME.headFontFace, objectName: "besoin minimal" });
texte(s, "frais juridiques et de marque (environ 3,1 k€ en année 1, dont 2,3 k€ HT de devis supposés) et déficit des premiers mois, si la publicité attend les mesures", { x: 0.5, y: 2.0, w: 3.6, h: 1.0, fontSize: 12, color: C.accent5, objectName: "besoin minimal legende" });
texte(s, "18 k€", { x: 0.5, y: 3.1, w: 3.6, h: 0.65, fontSize: 32, bold: true, color: C.accent2, fontFace: THEME.headFontFace, objectName: "besoin maximal" });
texte(s, "scénario central avec le plan publicitaire : la publicité y coûte plus qu'elle ne rapporte", { x: 0.5, y: 3.75, w: 3.6, h: 0.7, fontSize: 12, color: C.accent5, objectName: "besoin maximal legende" });
s.addShape(pres.ShapeType.roundRect, { x: 4.35, y: 1.2, w: 5.15, h: 3.75, rectRadius: 0.08, fill: { color: C.background1 }, line: { type: "none" }, objectName: "fond graphique sensibilite" });
// Graphique ajouté par ajouter_graphiques.py.
texte(s, "Pistes à étudier, sans recommandation : apport personnel, prêt d'honneur, aides à l'innovation (non vérifiées). Prochaine étape : lever les prérequis et mesurer la conversion.", { x: 0.5, y: 4.55, w: 3.6, h: 0.6, fontSize: 10, color: C.accent5, objectName: "pistes financement" });
s.addNotes("Trésorerie la plus basse sur 36 mois, départ à 0 € : ambitieux 3,6 k€, central sans publicité 3,8 k€, prudent 15,9 k€, central avec publicité 18,0 k€. Variantes du graphique : perte mensuelle des abonnés de 7 % au lieu de 10 % ; gratuit limité à 25 questions par mois en moyenne au lieu de 45 ; conversion mensuelle de 2 % au lieu de 1,2 % ; sans publicité payante ; et les trois derniers leviers réunis. Aucune aide ni prêt n'a été vérifié dans ce document ; ce n'est pas un conseil financier.");

(async () => {
  await pres.writeFile({ fileName: SORTIE });
  const theme = process.argv[2];
  if (theme) {
    const { applyTheme } = require(theme);
    await applyTheme(SORTIE, THEME);
  }
  console.log(SORTIE);
})();
