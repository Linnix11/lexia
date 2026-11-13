import { QuizModal } from './components/QuizModal'
import { Sidebar, Toast, Topbar } from './components/Layout'
import { SourcePanel } from './components/SourcePanel'
import { AppProvider } from './state/AppState'
import { useApp } from './state/contexte'
import { VueAssistant, VueBibliotheque, VueEspace, VueFiches, VueMatieres } from './views/Vues'
import { BandeauEmail } from './site/VerifierEmail'

function Contenu() {
  const { vue } = useApp()
  return (
    <main className="min-w-0">
      <Topbar />
      <div className="mx-auto max-w-[1300px] px-4 pt-6 pb-6 min-[361px]:px-4 tab:px-[22px] tab:pt-[29px] desk:px-[38px] desk:pt-9 desk:pb-[52px]">
        {vue === 'espace' && <VueEspace />}
        {vue === 'assistant' && <VueAssistant />}
        {vue === 'matieres' && <VueMatieres />}
        {vue === 'fiches' && <VueFiches />}
        {vue === 'bibliotheque' && <VueBibliotheque />}
        <footer className="pt-5 text-[10px] leading-[1.6] text-[#5f6762] tab:flex tab:justify-between tab:gap-3.5">
          <span className="block">Lexia · étude du droit français</span>
          <span className="mt-1 block tab:mt-0">Les citations ouvrent la source, la date et la version utilisées.</span>
        </footer>
      </div>
    </main>
  )
}

export default function App() {
  return (
    <AppProvider>
      <BandeauEmail />
      <div className="min-h-screen pb-[61px] tab:grid tab:grid-cols-[68px_minmax(0,1fr)] tab:pb-0 desk:grid-cols-[232px_minmax(0,1fr)]">
        <Sidebar />
        <Contenu />
      </div>
      {/* Ordre voulu : une source ouverte depuis un corrige de questionnaire s'affiche par-dessus. */}
      <QuizModal />
      <SourcePanel />
      <Toast />
    </AppProvider>
  )
}
