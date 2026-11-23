import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'
import Site from './Site'
import './index.css'

const racine = document.getElementById('root')!
const site = (
  <StrictMode>
    <Site />
  </StrictMode>
)
// Pages publiques compilees en HTML a la publication (D116) : React reprend le HTML present au lieu de le
// redessiner. Les autres pages (espace etudiant, connexion) arrivent vides et sont dessinees par le navigateur.
// Les pages de contenu sont chargees a part : leur module est telecharge avant l'hydratation. Sinon la reponse de
// la session, arrivee avant lui, obligerait React a redessiner la page (ecran de chargement visible un instant).
const contenu = /^\/(matieres|guides)(\/|$)/.test(window.location.pathname)
if (racine.firstElementChild) {
  ;(contenu ? import('./site/PagesContenu') : Promise.resolve()).catch(() => undefined).finally(() => hydrateRoot(racine, site))
} else createRoot(racine).render(site)
