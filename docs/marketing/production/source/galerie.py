#!/usr/bin/env python3
"""Page galerie et planning du mois 1 (production/galerie.html), lue depuis visuels/manifeste.json.

La page fonctionne ouverte en local (chemins relatifs) et publiee comme page claude.ai avec ses fichiers.
"""
import json
from pathlib import Path

PROD = Path(__file__).resolve().parent.parent
MANIFESTE = json.loads((PROD / "visuels" / "manifeste.json").read_text(encoding="utf-8"))

DOCUMENTS = [
    ("Storyboard V1 · Cas pratique en 30 s", "videos/storyboard-V1.pdf"),
    ("Storyboard V2 · 3 erreurs en L1", "videos/storyboard-V2.pdf"),
    ("Storyboard V3 · Le piège du 1382", "videos/storyboard-V3.pdf"),
    ("Storyboard V4 · Blanco en 45 s", "videos/storyboard-V4.pdf"),
    ("Storyboard V5 · Un quiz en 2 minutes", "videos/storyboard-V5.pdf"),
    ("Kit ambassadeur", "ambassadeurs/kit-ambassadeur.pdf"),
    ("Flyer A5", "impression/flyer-a5.pdf"),
    ("Dossier de presse", "presse/dossier-de-presse.pdf"),
]

PAGE = r"""<title>Lexia, mois 1</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gelasio:wght@400&family=Inter:wght@400;600;700&display=swap">
<style>
/* Mise en page : en-tete, calendrier de 4 semaines (lundi a dimanche), puis une bande de visuels par publication. */
:root {
  --paper: #f5f4ef; --surface: #fffefa; --line: #e4e4dc; --ink: #202724; --muted: #5f6762;
  --forest: #315e4b; --mint: #e7efe9; --gold: #bd8951; --brick: #8c4a36; --cream: #fbf7ef; --ochre: #746347;
  --c-video: #315e4b; --c-ig: #8c4a36; --c-li: #3c5a7a; --c-story: #746347;
  --serif: Gelasio, Georgia, "Times New Roman", serif; --sans: Inter, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --paper: #151a18; --surface: #1d2421; --line: #313a36; --ink: #e8ece9; --muted: #a9b3ae;
  --forest: #8fc0a8; --mint: #24332c; --gold: #d3a46f; --brick: #e0a08b; --cream: #262620; --ochre: #d6c29d;
  --c-video: #8fc0a8; --c-ig: #e0a08b; --c-li: #9ab8d8; --c-story: #d6c29d; color-scheme: dark } }
:root[data-theme="dark"] {
  --paper: #151a18; --surface: #1d2421; --line: #313a36; --ink: #e8ece9; --muted: #a9b3ae;
  --forest: #8fc0a8; --mint: #24332c; --gold: #d3a46f; --brick: #e0a08b; --cream: #262620; --ochre: #d6c29d;
  --c-video: #8fc0a8; --c-ig: #e0a08b; --c-li: #9ab8d8; --c-story: #d6c29d; color-scheme: dark }
body { background: var(--paper); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.55; }
.enveloppe { max-width: 1180px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 40px; }
h1, h2, h3 { font-family: var(--serif); font-weight: 400; line-height: 1.15; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(32px, 5vw, 48px); } h2 { font-size: 28px; } h3 { font-size: 20px; }
p { margin: 0; }
.surtitre { font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--forest); }
.tete { display: flex; flex-direction: column; gap: 14px; max-width: 760px; }
.tete .intro { color: var(--muted); font-size: 16px; }
.alerte { background: var(--cream); border-left: 3px solid var(--gold); padding: 12px 16px; color: var(--ochre);
  border-radius: 0 8px 8px 0; max-width: 760px; }
.chiffres { display: flex; flex-wrap: wrap; gap: 10px 28px; font-size: 14px; color: var(--muted); }
.chiffres b { font-family: var(--serif); font-weight: 400; font-size: 26px; color: var(--ink); margin-right: 6px;
  font-variant-numeric: lining-nums; }
.legende { display: flex; flex-wrap: wrap; gap: 8px 16px; font-size: 13px; color: var(--muted); }
.pastille { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.calendrier { overflow-x: auto; }
.grille { display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr)); gap: 6px; min-width: 860px; }
.jour-nom { font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
  padding: 0 4px 4px; }
.case { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 8px; min-height: 92px;
  display: flex; flex-direction: column; gap: 6px; }
.case .date { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
.semaine-titre { grid-column: 1 / -1; font-family: var(--serif); font-size: 17px; padding: 10px 4px 2px; }
.pub { display: block; text-decoration: none; color: var(--ink); font-size: 12.5px; line-height: 1.35; padding: 5px 7px;
  border-radius: 6px; background: var(--paper); border-left: 3px solid var(--forest); }
.pub:hover, .pub:focus-visible { background: var(--mint); }
.pub b { font-weight: 700; margin-right: 4px; }
:focus-visible { outline: 2px solid var(--forest); outline-offset: 2px; }
.liste { display: flex; flex-direction: column; gap: 28px; }
.bloc { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 18px;
  display: flex; flex-direction: column; gap: 12px; min-width: 0; scroll-margin-top: 16px; }
.bloc-tete { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; }
.bloc-tete .id { font-family: var(--serif); font-size: 22px; color: var(--forest); font-variant-numeric: lining-nums; }
.meta { font-size: 13px; color: var(--muted); }
.bande { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 6px; }
.bande button { flex: none; border: 1px solid var(--line); border-radius: 8px; padding: 0; background: var(--paper);
  cursor: zoom-in; overflow: hidden; }
.bande img { display: block; height: 220px; width: auto; max-width: none; }
.bande img.large { height: 150px; }
.liens { display: flex; flex-wrap: wrap; gap: 8px; }
.lien { font-size: 13px; font-weight: 600; color: var(--forest); text-decoration: none; border: 1px solid var(--line);
  border-radius: 999px; padding: 4px 12px; background: var(--paper); }
.lien:hover { background: var(--mint); }
.docs { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.doc { display: flex; justify-content: space-between; align-items: center; gap: 10px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; color: var(--ink); text-decoration: none; }
.doc:hover { border-color: var(--forest); }
.doc span { font-size: 12px; color: var(--muted); }
.reste ol { margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 6px; max-width: 760px; }
dialog { border: none; padding: 0; background: transparent; max-width: 96vw; max-height: 94vh; }
dialog::backdrop { background: rgba(10, 14, 12, .82); }
dialog img { display: block; max-width: 96vw; max-height: 86vh; width: auto; height: auto; border-radius: 8px; }
dialog .barre { display: flex; justify-content: space-between; gap: 12px; color: #fff; font-size: 13px; padding: 8px 2px; }
dialog button { background: #fffefa; color: #202724; border: none; border-radius: 6px; padding: 6px 12px; font: inherit;
  font-weight: 600; cursor: pointer; }
@media (max-width: 620px) { .bande img { height: 170px; } .bande img.large { height: 110px; } }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
html { scroll-behavior: smooth; }
</style>

<div class="enveloppe">
  <header class="tete">
    <p class="surtitre">Réseaux sociaux · 30 novembre au 27 décembre 2026</p>
    <h1>Lexia, mois 1 : planning et visuels</h1>
    <p class="intro">Les 26 publications du premier mois, prêtes à poster : calendrier, visuels aux bons formats,
      storyboards des vidéos et documents. Rien n'est publié ; les comptes n'existent pas encore.</p>
    <div class="chiffres" id="chiffres"></div>
  </header>

  <p class="alerte">À publier seulement après le passage de l'API Gemini au niveau payant et l'avis sur la marque
    « Lexia » (plan marketing, partie 1). Chiffres et dates relus sur le site le 23 novembre 2026 : à relire le jour de
    chaque publication.</p>

  <section aria-labelledby="t-cal" style="display:flex;flex-direction:column;gap:12px">
    <h2 id="t-cal">Calendrier</h2>
    <div class="legende" id="legende"></div>
    <div class="calendrier"><div class="grille" id="grille"></div></div>
  </section>

  <section aria-labelledby="t-docs" style="display:flex;flex-direction:column;gap:12px">
    <h2 id="t-docs">Storyboards et documents</h2>
    <div class="docs" id="docs"></div>
  </section>

  <section aria-labelledby="t-vis" style="display:flex;flex-direction:column;gap:12px">
    <h2 id="t-vis">Visuels par publication</h2>
    <p class="meta">Cliquez sur une image pour l'agrandir. Les légendes à coller sont dans
      <code>docs/marketing/production/calendrier-mois-1.md</code>.</p>
    <div class="liste" id="liste"></div>
  </section>

  <section class="reste" aria-labelledby="t-reste" style="display:flex;flex-direction:column;gap:12px">
    <h2 id="t-reste">Ce qui reste à faire</h2>
    <ol>
      <li>Passer l'API Gemini au niveau payant ; faire apprécier le nom « Lexia » par un conseil en propriété industrielle.</li>
      <li>Créer les comptes TikTok, Instagram, YouTube et la page LinkedIn (type professionnel, double authentification).</li>
      <li>Valider l'identité : logos définitifs, polices, couleurs ; relancer les générateurs si besoin.</li>
      <li>Tourner les vidéos avec les storyboards, sur un compte de test, et choisir la musique dans une bibliothèque gratuite.</li>
      <li>Compléter le dossier de presse (biographie, citation, photo) ; ajouter des captures de l'espace étudiant.</li>
      <li>Faire développer l'envoi des e-mails d'information (réservés aux comptes qui ont consenti) ; intégrer les pages d'atterrissage.</li>
      <li>Ambassadeurs : contrepartie, contrat relu par un avocat ; flyer : imprimeur choisi, impression après l'avis sur la marque.</li>
    </ol>
  </section>
</div>

<dialog id="zoom" aria-label="Visuel agrandi">
  <div class="barre"><span id="zoom-titre"></span><button type="button" id="zoom-fermer">Fermer</button></div>
  <img id="zoom-img" alt="">
</dialog>

<script>
const POSTS = __POSTS__;
const DOCS = __DOCS__;
const TYPES = [
  { cle: "video", nom: "Vidéo courte", couleur: "var(--c-video)", test: p => p.type.startsWith("Vidéo") },
  { cle: "story", nom: "Story", couleur: "var(--c-story)", test: p => /stor/i.test(p.type) },
  { cle: "li", nom: "LinkedIn", couleur: "var(--c-li)", test: p => p.reseaux.startsWith("LinkedIn") },
  { cle: "ig", nom: "Carrousel ou image", couleur: "var(--c-ig)", test: () => true },
];
const typeDe = p => TYPES.find(t => t.test(p));
const JOURS = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."];
const MOIS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];
const el = (tag, attrs = {}, ...enfants) => { const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === "style") e.style.cssText = v; else if (k === "text") e.textContent = v; else e.setAttribute(k, v); }
  for (const x of enfants) e.append(x); return e; };
const dateFr = iso => { const d = new Date(iso + "T12:00:00"); return `${d.getDate() === 1 ? "1er" : d.getDate()} ${MOIS[d.getMonth()]}`; };

const datees = POSTS.filter(p => p.date);
const nbVisuels = POSTS.reduce((n, p) => n + p.fichiers.length, 0);
const chiffres = document.getElementById("chiffres");
[[datees.length, "publications"], [nbVisuels, "visuels"], [datees.filter(p => p.type.startsWith("Vidéo")).length, "vidéos"],
 [5, "storyboards"], [4, "semaines"]].forEach(([n, l]) => chiffres.append(el("span", {}, el("b", { text: n }), l)));

const legende = document.getElementById("legende");
TYPES.forEach(t => legende.append(el("span", {}, el("span", { class: "pastille", style: `background:${t.couleur}` }), t.nom)));

const grille = document.getElementById("grille");
JOURS.forEach(j => grille.append(el("div", { class: "jour-nom", text: j })));
const debut = new Date("2026-11-30T12:00:00");
const titresSemaines = ["Semaine 1 · présentation", "Semaine 2 · méthode", "Semaine 3 · partiels", "Semaine 4 · fin d'année"];
for (let i = 0; i < 28; i++) {
  if (i % 7 === 0) grille.append(el("div", { class: "semaine-titre", text: titresSemaines[i / 7] }));
  const d = new Date(debut); d.setDate(debut.getDate() + i);
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const c = el("div", { class: "case" }, el("span", { class: "date", text: dateFr(iso) }));
  datees.filter(p => p.date === iso).forEach(p => {
    const a = el("a", { class: "pub", href: `#${p.id}`, style: `border-left-color:${typeDe(p).couleur}` }, el("b", { text: p.id }), p.titre);
    c.append(a);
  });
  grille.append(c);
}

const docs = document.getElementById("docs");
DOCS.forEach(([titre, chemin]) => docs.append(el("a", { class: "doc", href: chemin, target: "_blank", rel: "noopener" },
  titre, el("span", { text: "PDF" }))));

const zoom = document.getElementById("zoom"), zImg = document.getElementById("zoom-img"), zT = document.getElementById("zoom-titre");
document.getElementById("zoom-fermer").addEventListener("click", () => zoom.close());
zoom.addEventListener("click", e => { if (e.target === zoom) zoom.close(); });

const liste = document.getElementById("liste");
POSTS.forEach(p => {
  const t = typeDe(p);
  const tete = el("div", { class: "bloc-tete" }, el("span", { class: "id", text: p.id }), el("h3", { text: p.titre }),
    el("span", { class: "meta", text: [p.date ? dateFr(p.date) : "Modèle", p.reseaux, p.type].join(" · ") }));
  const bande = el("div", { class: "bande" });
  p.fichiers.forEach((f, i) => {
    const large = f.format === "1200x627";
    const img = el("img", { src: f.png, alt: `${p.id}, visuel ${i + 1} sur ${p.fichiers.length}, ${f.format}`, loading: "lazy", class: large ? "large" : "" });
    const b = el("button", { type: "button", "aria-label": `Agrandir ${p.id} visuel ${i + 1}` }, img);
    if (p.id === "AMB") b.style.background = "repeating-conic-gradient(var(--line) 0 25%, var(--surface) 0 50%) 0 0 / 20px 20px";
    b.addEventListener("click", () => { zImg.src = f.png; zImg.alt = img.alt; zT.textContent = `${p.id} · ${i + 1} / ${p.fichiers.length} · ${f.format}`; zoom.showModal(); });
    bande.append(b);
  });
  const liens = el("div", { class: "liens" });
  if (p.pdf) liens.append(el("a", { class: "lien", href: p.pdf, target: "_blank", rel: "noopener", text: "Document PDF pour LinkedIn" }));
  const bloc = el("article", { class: "bloc", id: p.id, style: `border-top:3px solid ${t.couleur}` }, tete, bande);
  if (p.pdf) bloc.append(liens);
  liste.append(bloc);
});
</script>
"""


def main() -> None:
    page = (PAGE.replace("__POSTS__", json.dumps(MANIFESTE, ensure_ascii=False))
                .replace("__DOCS__", json.dumps(DOCUMENTS, ensure_ascii=False)))
    (PROD / "galerie.html").write_text(page, encoding="utf-8")
    fichiers = sorted({f["png"] for p in MANIFESTE for f in p["fichiers"]} |
                      {p["pdf"] for p in MANIFESTE if p["pdf"]} | {d[1] for d in DOCUMENTS})
    (PROD / "source" / "galerie-fichiers.json").write_text(json.dumps(fichiers, indent=0), encoding="utf-8")
    print("galerie.html,", len(fichiers), "fichiers")


if __name__ == "__main__":
    main()
