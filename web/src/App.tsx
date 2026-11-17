import { QuizModal } from './components/QuizModal'
import { CadreEspace } from './components/Layout'
import { SourcePanel } from './components/SourcePanel'
import { useApp } from './state/contexte'
import { VueAssistant, VueBibliotheque, VueEspace, VueFiches, VueMatieres } from './views/Vues'

function Contenu() {
  const { vue } = useApp()
  return (
    <>
      {vue === 'espace' && <VueEspace />}
      {vue === 'assistant' && <VueAssistant />}
      {vue === 'matieres' && <VueMatieres />}
      {vue === 'fiches' && <VueFiches />}
      {vue === 'bibliotheque' && <VueBibliotheque />}
    </>
  )
}

export default function App() {
  return (
    <>
      <CadreEspace>
        <Contenu />
      </CadreEspace>
      {/* Ordre voulu : une source ouverte depuis un corrige de questionnaire s'affiche par-dessus. */}
      <QuizModal />
      <SourcePanel />
    </>
  )
}
