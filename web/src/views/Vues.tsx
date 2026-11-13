import { useState, type FormEvent } from 'react'
import { CarteBibliotheque, CarteOutils, CarteSources } from '../components/Cartes'
import { CarteAnnales } from '../components/Annales'
import { Chat } from '../components/Chat'
import { DepotCours, ListeCoursMatiere } from '../components/MesCours'
import { Card, CardHead } from '../components/Layout'
import { Reponse } from '../components/Reponse'
import { MODES } from '../lib/modes'
import { useApp } from '../state/contexte'

const dateDuJour = () => {
  const d = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
  return d.charAt(0).toUpperCase() + d.slice(1)
}

function EnTete({ surtitre, titre, texte, droite }: { surtitre: string; titre: string; texte: string; droite?: string }) {
  return (
    <div className="mb-[19px] tab:mb-[25px] tab:flex tab:items-end tab:justify-between tab:gap-5">
      <div>
        <div className="text-[10px] font-bold tracking-[1.6px] text-forest uppercase">{surtitre}</div>
        <h1 className="mt-[9px] mb-[7px] font-display text-[28px] leading-[1.1] font-normal tracking-[-.8px] min-[361px]:text-[31px] tab:text-[36px]">
          {titre}
        </h1>
        <p className="text-muted">{texte}</p>
      </div>
      {droite && <div className="mt-3 pb-[3px] text-[11px] text-muted tab:mt-0">{droite}</div>}
    </div>
  )
}

const corpus = <span className="rounded-full bg-mint px-[9px] py-1.5 text-[10px] whitespace-nowrap text-forest">● Corpus officiel</span>

export function VueEspace() {
  return (
    <>
      <EnTete surtitre={dateDuJour()} titre="Bonjour, Étudiant·e."
        texte="Votre espace pour comprendre le droit et progresser à votre rythme." droite="Droit français · Licence" />
      <div className="grid items-start gap-[19px] tab:grid-cols-[minmax(0,1.2fr)_minmax(235px,.8fr)] desk:grid-cols-[minmax(0,1.65fr)_minmax(260px,.85fr)]">
        <div className="grid min-w-0 gap-[18px]">
          <Card className="flex min-w-0 flex-col px-4 py-[18px] tab:px-[22px] tab:pt-[21px] tab:pb-[17px]">
            <CardHead titre="Assistant d’étude" sousTitre="Des explications appuyées sur des sources vérifiables" droite={corpus} />
            <Chat />
          </Card>
          <CarteOutils />
          <DepotCours />
        </div>
        <div className="grid min-w-0 gap-[18px]">
          <CarteSources />
          <CarteBibliotheque />
        </div>
      </div>
    </>
  )
}

export function VueAssistant() {
  return (
    <>
      <EnTete surtitre="Assistant IA" titre="Posez votre question."
        texte="Choisissez le type d’aide : explication, fiche, cas pratique, commentaire d’arrêt ou dissertation." />
      <Card className="mx-auto flex max-w-[900px] flex-col px-4 py-[18px] tab:px-[22px] tab:pt-[21px] tab:pb-[17px]">
        <CardHead titre="Assistant d’étude" sousTitre="Cliquez sur une référence [S1] pour lire la source" droite={corpus} />
        <div className="mt-4 flex flex-1 flex-col"><Chat complet /></div>
      </Card>
    </>
  )
}

export function VueMatieres() {
  const { matieres, setMatiere, setVue, ouvrirQuiz } = useApp()
  return (
    <>
      <EnTete surtitre="Mes matières" titre="Matières suivies." texte="Chaque matière s’appuie sur des sources officielles, et sur les cours que vous déposez." />
      <DepotCours />
      {matieres.length === 0 ? (
        <Card className="p-6 text-[12px] text-muted">Impossible de charger les matières : vérifiez que l’API Lexia est démarrée.</Card>
      ) : (
        <div className="grid gap-[18px] tab:grid-cols-2 desk:grid-cols-3">
          {matieres.map((m) => (
            <Card key={m.id} className="flex flex-col p-[19px]">
              <h2 className="font-display text-[21px]">{m.libelle}</h2>
              <ul className="mt-3 mb-4 grid gap-1.5 text-[11px] text-muted">
                {m.sources.map((s) => <li key={s}>· {m.noms_sources?.[s] ?? s}</li>)}
              </ul>
              <ListeCoursMatiere matiere={m.id} />
              <div className="mt-auto flex flex-wrap gap-2">
                <button type="button" onClick={() => { setMatiere(m.id); setVue('assistant') }}
                  className="rounded-[7px] bg-forest px-3 py-2 text-[11px] text-white hover:bg-forest-dark">Poser une question</button>
                <button type="button" onClick={() => { setMatiere(m.id); ouvrirQuiz() }}
                  className="rounded-[7px] border border-line px-3 py-2 text-[11px] text-forest hover:border-[#9eafa3]">S’entraîner</button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}

export function VueFiches() {
  const { favoris, basculerFavori, envoyer, setVue, ouvrirQuiz } = useApp()
  const [ouverte, setOuverte] = useState<string | null>(null)
  const [theme, setTheme] = useState('')
  const creer = (e: FormEvent) => {
    e.preventDefault()
    if (theme.trim().length < 3) return
    setVue('assistant')
    envoyer(`Fais-moi une fiche de révision sur ${theme.trim()}`, 'fiche')
    setTheme('')
  }
  return (
    <>
      <EnTete surtitre="Fiches & révisions" titre="Vos fiches." texte="Les réponses enregistrées restent dans ce navigateur uniquement." />
      <Card className="mb-[18px] p-4 tab:p-[19px]">
        <form onSubmit={creer} className="flex flex-wrap items-end gap-2">
          <label className="grid min-w-[220px] flex-1 gap-1.5 text-[11px] text-muted">
            Nouvelle fiche sur…
            <input value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="Ex. la force obligatoire du contrat"
              className="rounded-[7px] border border-line bg-white p-[9px] text-[12px] text-ink" />
          </label>
          <button type="submit" className="rounded-[7px] bg-forest px-3 py-[9px] text-[12px] text-white hover:bg-forest-dark">Créer la fiche</button>
          <button type="button" onClick={() => ouvrirQuiz(theme)} className="rounded-[7px] border border-line px-3 py-[9px] text-[12px] text-forest hover:border-[#9eafa3]">
            Quiz sur ce thème
          </button>
        </form>
      </Card>
      {favoris.length === 0 ? (
        <Card className="p-6 text-center">
          <p className="font-display text-[19px]">Aucune fiche enregistrée pour l’instant.</p>
          <p className="mt-1.5 text-[12px] text-muted">Les fiches créées ici ou avec le mode « Fiche » de l’assistant s’enregistrent automatiquement. Vous pouvez aussi enregistrer n’importe quelle réponse avec « Enregistrer en fiche ».</p>
          <button type="button" onClick={() => setVue('assistant')} className="mt-4 rounded-[7px] bg-forest px-3 py-2 text-[12px] text-white hover:bg-forest-dark">
            Ouvrir l’assistant
          </button>
        </Card>
      ) : (
        <ul className="grid gap-2.5">
          {favoris.map((f) => (
            <li key={f.id}>
              <Card className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <button type="button" className="min-w-0 flex-1 text-left" aria-expanded={ouverte === f.id}
                    onClick={() => setOuverte(ouverte === f.id ? null : f.id)}>
                    <span className="block font-display text-[17px]">{f.reponse.titre || f.question}</span>
                    <span className="mt-1 block text-[11px] text-muted">
                      {MODES.find((m) => m.id === f.mode)?.label} · {new Date(f.enregistre_le).toLocaleDateString('fr-FR')} · {f.reponse.sources.length} source(s)
                    </span>
                  </button>
                  <button type="button" onClick={() => basculerFavori({ id: f.id, question: f.question, mode: f.mode, etat: 'ok', reponse: f.reponse })}
                    className="text-[11px] text-muted hover:text-[#8c4a36]">Retirer</button>
                </div>
                {ouverte === f.id && (
                  <div className="mt-3">
                    <Reponse message={{ id: f.id, question: f.question, mode: f.mode, etat: 'ok', reponse: f.reponse }} actions={false} />
                  </div>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export function VueBibliotheque() {
  return (
    <>
      <EnTete surtitre="Bibliothèque" titre="Ressources et manuels." texte="Sources officielles du corpus, annales d’examens et références à consulter en bibliothèque." />
      <div className="grid items-start gap-[18px] tab:grid-cols-2">
        <CarteSources />
        <CarteBibliotheque complete />
        <CarteAnnales />
      </div>
      <p className="mt-4 text-[11px] text-muted">
        Les bibliographies recommandées par les facultés partenaires seront ajoutées ici (métadonnées et liens uniquement).
      </p>
    </>
  )
}
