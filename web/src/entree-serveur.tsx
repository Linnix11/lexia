// Entree du prerendu (D116), compilee par `vite build --ssr` et appelee par web/scripts/prerendu.mjs avec un
// document jsdom dont l'adresse est celle de la page a rendre. Le site est rendu tel quel : meme arbre que dans
// le navigateur, pour que React reprenne le HTML sans le redessiner (hydrateRoot dans main.tsx).
import { StrictMode } from 'react'
import { prerender } from 'react-dom/static'
import Site from './Site'

export { pagesSeo } from './site/seo'
export { fichierPage, llmsTxt, pageHtml, sitemapXml } from './site/publication'

/** HTML de la page a l'adresse courante (window.location), Suspense et pages chargees a part comprises. */
export async function rendre(): Promise<string> {
  const { prelude } = await prerender(
    <StrictMode>
      <Site />
    </StrictMode>,
  )
  return new Response(prelude).text()
}
