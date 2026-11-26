import { useState, type FormEvent } from 'react'
import { CarteBibliotheque, CarteOutils, CarteSources } from '../components/Cartes'
import { CarteAnnales } from '../components/Annales'
import { CarteMentale } from '../components/CarteMentale'
import { RechercheBibliotheque } from '../components/RechercheBibliotheque'
import { Chat } from '../components/Chat'
import { ChoixAnnee } from '../components/ChoixAnnee'
import { DepotCours, ListeCoursMatiere } from '../components/MesCours'
import { Card, CardHead } from '../components/Layout'
import { Reponse } from '../components/Reponse'
import { CarteRevisions, SeanceRevision } from '../components/Revision'
import { aReviser, carteDeFiche } from '../lib/cartes'
import { filtrerCartes, lireCartesMentales, retirerCarteMentale, type CarteEnregistree } from '../lib/cartesEnregistrees'
import { ficheEnMarkdown, fichesEnMarkdown, imprimerFiche, nomFichier, telecharger } from '../lib/exportFiches'
import { filtrerFiches, matieresDesFiches } from '../lib/favoris'
import { libelleFraicheur, useFraicheur } from '../lib/fraicheur'
import { ANNEES, filtrerMatieres, grouperParAnnee, LIBELLES_ANNEES, sourcesPrincipales, type Annee } from '../lib/matieres'
import { MODES } from '../lib/modes'
import { phraseQuestionsRestantes, salutation, tronquer } from '../lib/personnalisation'
import { Lien } from '../lib/router'
import { libelleSemestre } from '../lib/semestres'
import { useApp } from '../state/contexte'
import { useSession } from '../state/session'

const dateDuJour = () => {
  const d = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
  return d.charAt(0).toUpperCase() + d.slice(1)
}

function EnTete({ surtitre, titre, texte, droite }: { surtitre: string; titre: string; texte: string; droite?: string }) {
  return (
    <div className="mb-[19px] tab:mb-[25px] tab:flex tab:items-end tab:justify-between tab:gap-5">
      <div>
        <div className="text-[12px] font-bold tracking-[1.6px] text-forest uppercase">{surtitre}</div>
        <h1 className="mt-[9px] mb-[7px] font-display text-[28px] leading-[1.1] font-normal tracking-[-.8px] min-[361px]:text-[31px] tab:text-[36px]">
          {titre}
        </h1>
        <p className="text-muted">{texte}</p>
      </div>
      {droite && <div className="mt-3 pb-[3px] text-[12px] text-muted tab:mt-0">{droite}</div>}
    </div>
  )
}

const corpus = <span className="rounded-full bg-mint px-[9px] py-1.5 text-[12px] whitespace-nowrap text-forest">● Corpus officiel</span>

/** De quoi reprendre la ou l'on s'etait arrete (D100) : questionnaire commence, dernier cours, derniere fiche. */
function CarteReprendre() {
  const { dernierQuiz, ouvrirQuiz, mesCours, setMatiere, setCoursChoisis, setVue, favoris, cartes } = useApp()
  const quiz = dernierQuiz.quiz?.quiz_id && !dernierQuiz.correction ? dernierQuiz.quiz : null
  const cours = mesCours.filter((c) => c.statut !== 'traitement').reduce<(typeof mesCours)[number] | null>(
    (dernier, c) => (!dernier || c.ajoute_le > dernier.ajoute_le ? c : dernier), null)
  const fiche = favoris[0] ?? null
  const dues = aReviser(cartes).length
  if (!quiz && !cours && !fiche && !dues) return null
  const ligne = 'flex items-center justify-between gap-3 border-t border-line-soft py-2.5 first:border-t-0 first:pt-0 last:pb-0'
  const action = 'shrink-0 rounded-[7px] border border-line px-2.5 py-1.5 text-[12px] text-forest hover:border-[#9eafa3]'
  return (
    <Card className="p-[18px]">
      <CardHead titre="Pour reprendre" />
      <ul className="mt-3 text-[12px]">
        {quiz && (
          <li className={ligne}>
            <span className="min-w-0">Questionnaire commencé : « {tronquer(quiz.theme, 50)} »</span>
            <button type="button" onClick={() => ouvrirQuiz()} className={action}>Reprendre</button>
          </li>
        )}
        {cours && (
          <li className={ligne}>
            <span className="min-w-0">Dernier cours déposé : « {tronquer(cours.titre, 50)} »</span>
            <button type="button" className={action}
              onClick={() => { setMatiere(cours.matiere); setCoursChoisis([cours.id]); setVue('assistant') }}>L’interroger</button>
          </li>
        )}
        {dues > 0 && (
          <li className={ligne}>
            <span className="min-w-0">{dues} carte{dues > 1 ? 's' : ''} à revoir aujourd’hui</span>
            <button type="button" onClick={() => setVue('fiches')} className={action}>Réviser</button>
          </li>
        )}
        {fiche && (
          <li className={ligne}>
            <span className="min-w-0">Dernière fiche : « {tronquer(fiche.question, 50)} »</span>
            <button type="button" onClick={() => setVue('fiches')} className={action}>Revoir</button>
          </li>
        )}
      </ul>
    </Card>
  )
}

export function VueEspace() {
  const { profil } = useSession()
  const { matiere, matieres, semestre } = useApp()
  const restant = profil ? Math.max(0, profil.formule.questions_par_jour - profil.usage.questions) : null
  const libelleMatiere = matieres.find((m) => m.id === matiere)?.libelle ?? 'Toutes les matières'
  return (
    <>
      <EnTete surtitre={dateDuJour()} titre={salutation(profil?.prenom)}
        texte={`Votre espace pour comprendre le droit et progresser à votre rythme.${
          restant === null ? '' : ` ${phraseQuestionsRestantes(restant, profil!.formule.questions_par_jour)}`}`}
        droite={`${libelleMatiere} · ${libelleSemestre(semestre)}`} />
      {profil && (!profil.prenom || !profil.nom) && (
        // Comptes crees avant D102 : invites a completer, jamais bloques.
        <p className="mb-[18px] rounded-xl border border-line bg-surface px-4 py-3 text-[12px] text-muted">
          Ajoutez votre prénom et votre nom pour que Lexia vous salue par votre prénom.{' '}
          <Lien href="/compte" className="font-semibold text-forest hover:underline">Compléter dans Mon compte</Lien>
        </p>
      )}
      <div className="grid items-start gap-[19px] tab:grid-cols-[minmax(0,1.2fr)_minmax(235px,.8fr)] desk:grid-cols-[minmax(0,1.65fr)_minmax(260px,.85fr)]">
        <div className="grid min-w-0 gap-[18px]">
          <ChoixAnnee />
          <Card className="flex min-w-0 flex-col px-4 py-[18px] tab:px-[22px] tab:pt-[21px] tab:pb-[17px]">
            <CardHead titre="Assistant d’étude" sousTitre="Des explications appuyées sur des sources vérifiables" droite={corpus} />
            <Chat />
          </Card>
          <CarteOutils />
        </div>
        <div className="grid min-w-0 gap-[18px]">
          <CarteReprendre />
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
      <ChoixAnnee className="mx-auto mb-[18px] max-w-[900px]" />
      <Card className="mx-auto flex max-w-[900px] flex-col px-4 py-[18px] tab:px-[22px] tab:pt-[21px] tab:pb-[17px]">
        <CardHead titre="Assistant d’étude" sousTitre="Cliquez sur une référence [1] pour lire la source" droite={corpus} />
        <div className="mt-4 flex flex-1 flex-col"><Chat complet /></div>
      </Card>
    </>
  )
}

export function VueMatieres() {
  const { matieres, setMatiere, setVue, ouvrirQuiz, niveau } = useApp()
  const fraicheur = useFraicheur()
  const [recherche, setRecherche] = useState('')
  const [annee, setAnnee] = useState<Annee | null>(null)
  // Classement par annee de licence et recherche sur les intitules des maquettes et les sources (D97).
  const groupes = grouperParAnnee(filtrerMatieres(matieres, recherche)).filter((g) => !annee || g.annee === annee)
  const puce = (actif: boolean) => `rounded-full border px-2.5 py-1.5 text-[12px] ${
    actif ? 'border-forest bg-mint font-semibold text-forest' : 'border-line bg-chip text-[#59615b] hover:border-[#9eafa3]'}`
  return (
    <>
      <EnTete surtitre="Mes matières" titre="Matières disponibles." texte="Chaque matière s’appuie sur des sources officielles, et sur les cours que vous déposez." />
      <DepotCours />
      {matieres.length === 0 ? (
        // liste vide aussi pendant le chargement (et ses essais) : pas de message d'erreur (audit du 2026-11-18, D9)
        <Card className="p-6 text-[12px] text-muted"><p role="status">Chargement des matières… Si elles n’apparaissent pas, rechargez la page.</p></Card>
      ) : (
        <>
          <div className="mb-[18px] flex flex-wrap items-center gap-2">
            {/* Bordure a 3:1 et contour au focus sur le label : le champ est en outline-none (audit du 2026-11-23, D3) */}
            <label className="flex min-w-[240px] flex-1 items-center gap-2 rounded-[7px] border border-[#878f88] bg-white px-3 py-2 text-[12px] text-muted focus-within:border-forest focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-forest">
              <span className="sr-only">Chercher une matière</span>
              <span aria-hidden>⌕</span>
              <input type="search" value={recherche} onChange={(e) => setRecherche(e.target.value)}
                placeholder="Chercher une matière : procédure pénale, sociétés, Code civil…"
                className="min-w-0 flex-1 bg-transparent text-ink outline-none" />
            </label>
            <div role="group" aria-label="Année de licence" className="flex flex-wrap gap-1.5">
              <button type="button" aria-pressed={annee === null} onClick={() => setAnnee(null)} className={puce(annee === null)}>Toutes</button>
              {ANNEES.map((a) => (
                <button key={a} type="button" aria-pressed={annee === a} onClick={() => setAnnee(annee === a ? null : a)} className={puce(annee === a)}>
                  {a}
                </button>
              ))}
            </div>
          </div>
          {groupes.length === 0 && (
            <Card className="p-6 text-[12px] text-muted">
              <p role="status">
                {recherche.trim() ? `Aucune matière ne correspond à « ${recherche.trim()} »` : 'Aucune matière'}
                {annee ? ` en ${LIBELLES_ANNEES[annee]}` : ''}. Lexia couvre le droit français et les
                traités de l’Union européenne (la Convention européenne des droits de l’homme et la Charte des Nations unies n’y
                sont pas encore). Vous pouvez aussi poser votre question avec la matière « Toutes ».
              </p>
            </Card>
          )}
          {groupes.map((g) => (
            <section key={g.titre} aria-labelledby={`annee-${g.annee ?? 'autres'}`} className="mb-[22px]">
              <h2 id={`annee-${g.annee ?? 'autres'}`} className="mb-2.5 text-[12px] font-bold tracking-[1.6px] text-forest uppercase">
                {g.titre}{g.annee && g.annee === niveau ? ' · votre année' : ''}
              </h2>
              <div className="grid gap-[18px] tab:grid-cols-2 desk:grid-cols-3">
                {g.matieres.map((m) => (
                  // Matiere, cours personnels et actions d'abord ; textes officiels replies (audit du 2026-11-16, point 7).
                  <Card key={m.id} className="flex flex-col self-start p-[19px]">
                    <h3 className="font-display text-[21px]">{m.libelle}</h3>
                    <p className="mt-1 text-[12px] text-muted">Sources principales : {sourcesPrincipales(m).join(' · ')}</p>
                    <div className="mt-3"><ListeCoursMatiere matiere={m.id} /></div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => { setMatiere(m.id); setVue('assistant') }}
                        className="rounded-[7px] bg-forest px-3 py-2 text-[12px] text-white hover:bg-forest-dark">Poser une question</button>
                      <button type="button" onClick={() => { setMatiere(m.id); ouvrirQuiz() }}
                        className="rounded-[7px] border border-line px-3 py-2 text-[12px] text-forest hover:border-[#9eafa3]">S’entraîner</button>
                    </div>
                    <div className="mt-2">
                      <CarteMentale avecNotion libelle="Carte mentale de la matière"
                        demande={(notion) => ({ type: 'matiere', matiere: m.id, notion })} />
                    </div>
                    <details className="mt-4 border-t border-line-soft pt-3 text-[12px] text-muted">
                      <summary className="cursor-pointer text-forest">Textes officiels ({m.sources.length})</summary>
                      <ul className="mt-2 grid gap-1.5">
                        {m.sources.map((s) => (
                          <li key={s}>
                            · {m.noms_sources?.[s] ?? s}
                            {fraicheur?.sources[s] && <span className="text-muted"> · {libelleFraicheur(fraicheur.sources[s])}</span>}
                          </li>
                        ))}
                      </ul>
                    </details>
                  </Card>
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </>
  )
}

export function VueFiches() {
  const { favoris, basculerFavori, envoyer, setVue, ouvrirQuiz, occupe, matieres, cartes, ajouterCartes } = useApp()
  const [ouverte, setOuverte] = useState<string | null>(null)
  const [theme, setTheme] = useState('')
  const [revision, setRevision] = useState<{ matiere: string | null } | null>(null) // seance en cours (D140 : matiere)
  // Bouton actif : la raison d'un refus est dite au clic plutot qu'en infobulle (audit du 2026-11-19, WEB-10)
  const [aide, setAide] = useState<string | null>(null)
  // Retrait d'une fiche en deux temps (WEB-20)
  const [aRetirer, setARetirer] = useState<string | null>(null)
  const [recherche, setRecherche] = useState('')
  // undefined : toutes les matieres ; null : fiches sans matiere
  const [filtreChoisi, setFiltre] = useState<string | null | undefined>(undefined)
  const groupes = matieresDesFiches(favoris, matieres)
  const filtre = groupes.some((g) => g.id === filtreChoisi) ? filtreChoisi : undefined // matiere videe par un retrait
  const visibles = filtrerFiches(favoris, recherche, filtre)
  const libelleMatiere = (id?: string | null) => (id ? matieres.find((m) => m.id === id)?.libelle ?? id : undefined)
  const puce = (actif: boolean) => `min-h-8 rounded-full border px-2.5 py-1 text-[11px] ${
    actif ? 'border-forest bg-mint font-semibold text-forest' : 'border-line bg-chip text-[#59615b] hover:border-[#9eafa3]'}`
  const creer = (e: FormEvent) => {
    e.preventDefault()
    if (occupe) return setAide('Une réponse est en cours : patientez quelques secondes.')
    if (theme.trim().length < 3) return setAide('Écrivez un thème d’au moins 3 caractères.')
    setAide(null)
    setVue('assistant')
    envoyer(`Fais-moi une fiche de révision sur ${theme.trim()}`, 'fiche')
    setTheme('')
  }
  return (
    <>
      <EnTete surtitre="Fiches & révisions" titre="Vos fiches."
        texte="Les fiches et les cartes restent dans ce navigateur uniquement : exportez les fiches pour les garder ailleurs ou les ouvrir sur un autre appareil." />
      {revision ? <SeanceRevision matiere={revision.matiere} onFin={() => setRevision(null)} />
        : <CarteRevisions onReviser={(matiere) => setRevision({ matiere })} />}
      {favoris.length > 0 && (
        <div className="mb-3 flex justify-end">
          <button type="button" onClick={() => telecharger('fiches-lexia.md', fichesEnMarkdown(favoris))}
            className="rounded-[7px] border border-line bg-surface px-3 py-2 text-[12px] text-forest hover:border-[#9eafa3]">
            Exporter toutes les fiches (.md)
          </button>
        </div>
      )}
      <Card className="mb-[18px] p-4 tab:p-[19px]">
        <form onSubmit={creer} className="flex flex-wrap items-end gap-2">
          <label className="grid min-w-[220px] flex-1 gap-1.5 text-[11px] text-muted">
            Nouvelle fiche sur…
            <input value={theme} onChange={(e) => { setTheme(e.target.value); setAide(null) }} placeholder="Ex. la force obligatoire du contrat"
              aria-describedby="aide-fiche" className="rounded-[7px] border border-line bg-white p-[9px] text-[12px] text-ink" />
          </label>
          <button type="submit"
            className="rounded-[7px] bg-forest px-3 py-[9px] text-[12px] text-white hover:bg-forest-dark disabled:opacity-60">Créer la fiche</button>
          <button type="button" onClick={() => ouvrirQuiz(theme)} className="rounded-[7px] border border-line px-3 py-[9px] text-[12px] text-forest hover:border-[#9eafa3]">
            Quiz sur ce thème
          </button>
          <p id="aide-fiche" role="status" className="w-full text-[12px] text-[#8c4a36] empty:hidden">{aide ?? ''}</p>
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
        <>
        {/* Recherche et classement par matiere (D139) : jusqu'a 100 fiches, la liste chronologique ne suffisait plus. */}
        <div className="mb-3 grid gap-2">
          <label className="flex min-w-0 items-center gap-2 rounded-[7px] border border-[#878f88] bg-white px-3 py-2 text-[12px] text-muted focus-within:border-forest focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-forest">
            <span className="sr-only">Chercher dans mes fiches</span>
            <span aria-hidden>⌕</span>
            <input type="search" value={recherche} onChange={(e) => setRecherche(e.target.value)}
              placeholder="Chercher : notion, article, arrêt…" className="min-w-0 flex-1 bg-transparent text-ink outline-none" />
          </label>
          {groupes.length > 1 && (
            <div role="group" aria-label="Matière" className="flex flex-wrap gap-1.5">
              <button type="button" aria-pressed={filtre === undefined} onClick={() => setFiltre(undefined)} className={puce(filtre === undefined)}>
                Toutes ({favoris.length})
              </button>
              {groupes.map((g) => (
                <button key={g.id ?? 'sans'} type="button" aria-pressed={filtre === g.id}
                  onClick={() => setFiltre(filtre === g.id ? undefined : g.id)} className={puce(filtre === g.id)}>
                  {g.libelle} ({g.nombre})
                </button>
              ))}
            </div>
          )}
        </div>
        {visibles.length < favoris.length && (
          <p role="status" className="mb-2 text-[12px] text-muted">
            {visibles.length === 0 ? 'Aucune fiche ne correspond.' : `${visibles.length} fiche${visibles.length > 1 ? 's' : ''} sur ${favoris.length}.`}
          </p>
        )}
        <ul className="grid gap-2.5">
          {visibles.map((f) => (
            <li key={f.id}>
              <Card className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <button type="button" className="min-w-0 flex-1 text-left" aria-expanded={ouverte === f.id}
                    onClick={() => setOuverte(ouverte === f.id ? null : f.id)}>
                    <span className="block font-display text-[17px]">{f.reponse.titre || f.question}</span>
                    <span className="mt-1 block text-[11px] text-muted">
                      {[MODES.find((m) => m.id === f.mode)?.label, libelleMatiere(f.matiere),
                        new Date(f.enregistre_le).toLocaleDateString('fr-FR'), `${f.reponse.sources.length} source(s)`].filter(Boolean).join(' · ')}
                    </span>
                  </button>
                  <span className="flex flex-wrap gap-x-3">
                    <button type="button" onClick={() => imprimerFiche(f, libelleMatiere(f.matiere))}
                      aria-label={`Imprimer ou PDF : fiche « ${f.reponse.titre || f.question} »`}
                      className="min-h-11 text-[11px] text-forest hover:underline">Imprimer ou PDF</button>
                    <button type="button" onClick={() => telecharger(nomFichier(f.reponse.titre || f.question), ficheEnMarkdown(f))}
                      aria-label={`Exporter (.md) la fiche « ${f.reponse.titre || f.question} »`}
                      className="min-h-11 text-[11px] text-forest hover:underline">Exporter (.md)</button>
                    {/* Vers la revision espacee (D104), sans la changer : la carte de cette fiche seulement */}
                    {cartes.some((c) => c.id === `fiche:${f.id}`) ? (
                      <span className="inline-flex min-h-11 items-center text-[11px] text-muted">Dans vos révisions</span>
                    ) : carteDeFiche(f) && (
                      <button type="button" onClick={() => ajouterCartes([carteDeFiche(f)!])}
                        aria-label={`Réviser cette fiche : « ${f.reponse.titre || f.question} »`}
                        className="min-h-11 text-[11px] text-forest hover:underline">Réviser cette fiche</button>
                    )}
                    <button type="button"
                      onClick={() => {
                        if (aRetirer !== f.id) return setARetirer(f.id)
                        setARetirer(null)
                        basculerFavori({ id: f.id, question: f.question, mode: f.mode, etat: 'ok', reponse: f.reponse })
                      }}
                      onBlur={() => setARetirer((x) => (x === f.id ? null : x))}
                      aria-label={aRetirer === f.id ? `Confirmer le retrait de « ${f.reponse.titre || f.question} »` : `Retirer la fiche « ${f.reponse.titre || f.question} »`}
                      className={`min-h-11 text-[11px] hover:text-[#8c4a36] ${aRetirer === f.id ? 'font-semibold text-[#8c4a36]' : 'text-muted'}`}>
                      {aRetirer === f.id ? 'Confirmer le retrait' : 'Retirer'}
                    </button>
                  </span>
                </div>
                {ouverte === f.id && (
                  <div className="mt-3">
                    <Reponse message={{ id: f.id, question: f.question, mode: f.mode, etat: 'ok', reponse: f.reponse }} actions={false} titre={false} />
                  </div>
                )}
              </Card>
            </li>
          ))}
        </ul>
        </>
      )}
    </>
  )
}

/** Cartes mentales enregistrees avec « Enregistrer la carte », dans ce navigateur (lib/cartesEnregistrees.ts). */
export function VueCartes() {
  const { setVue } = useApp()
  const compte = useSession().profil?.email ?? ''
  const [cartes, setCartes] = useState<CarteEnregistree[]>(() => lireCartesMentales(compte))
  const [ouverte, setOuverte] = useState<string | null>(null)
  const [aRetirer, setARetirer] = useState<string | null>(null)
  const [recherche, setRecherche] = useState('')
  const trouvees = filtrerCartes(cartes, recherche)
  return (
    <>
      <EnTete surtitre="Mes cartes mentales" titre="Vos cartes."
        texte="Les cartes enregistrées restent dans ce navigateur uniquement : imprimez-les, enregistrez-les en PDF ou en image (PNG) pour les garder ailleurs." />
      {/* Recherche des que la liste ne tient plus d'un coup d'oeil (50 cartes au plus, D138) */}
      {cartes.length > 3 && (
        <div className="mb-3">
          <label className="grid gap-1 text-[11px] text-muted">
            Rechercher une carte (titre, notion, article)
            <input type="search" value={recherche} onChange={(e) => setRecherche(e.target.value)}
              placeholder="ex. garde, 1242, imprévision"
              className="min-h-10 rounded-[7px] border border-line bg-white px-3 text-[13px] text-ink" />
          </label>
          <p className="mt-1 text-[11px] text-muted" aria-live="polite">
            {recherche.trim() ? `${trouvees.length} carte(s) sur ${cartes.length}` : `${cartes.length} cartes enregistrées`}
          </p>
        </div>
      )}
      {cartes.length > 0 && trouvees.length === 0 && (
        <p className="text-[12px] text-muted">Aucune carte ne correspond à « {recherche.trim()} ».</p>
      )}
      {cartes.length === 0 ? (
        <Card className="p-6 text-center">
          <p className="font-display text-[19px]">Aucune carte enregistrée pour l’instant.</p>
          <p className="mt-1.5 text-[12px] text-muted">
            Créez une carte mentale depuis une réponse, un cours déposé ou une matière, puis cliquez sur « Enregistrer la carte ».
          </p>
          <button type="button" onClick={() => setVue('assistant')} className="mt-4 rounded-[7px] bg-forest px-3 py-2 text-[12px] text-white hover:bg-forest-dark">
            Ouvrir l’assistant
          </button>
        </Card>
      ) : (
        <ul className="grid gap-2.5">
          {trouvees.map((c) => (
            <li key={c.id}>
              <Card className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <button type="button" className="min-w-0 flex-1 text-left" aria-expanded={ouverte === c.id}
                    onClick={() => setOuverte(ouverte === c.id ? null : c.id)}>
                    <span className="block font-display text-[17px]">{c.titre}</span>
                    <span className="mt-1 block text-[11px] text-muted">
                      Enregistrée le {new Date(c.enregistree_le).toLocaleDateString('fr-FR')} · {c.carte.branches.length} branche(s)
                    </span>
                  </button>
                  <button type="button"
                    onClick={() => {
                      if (aRetirer !== c.id) return setARetirer(c.id)
                      setARetirer(null)
                      if (ouverte === c.id) setOuverte(null)
                      setCartes(retirerCarteMentale(c.id, compte))
                    }}
                    onBlur={() => setARetirer((x) => (x === c.id ? null : x))}
                    aria-label={aRetirer === c.id ? `Confirmer le retrait de « ${c.titre} »` : `Retirer la carte « ${c.titre} »`}
                    className={`min-h-11 text-[11px] hover:text-[#8c4a36] ${aRetirer === c.id ? 'font-semibold text-[#8c4a36]' : 'text-muted'}`}>
                    {aRetirer === c.id ? 'Confirmer le retrait' : 'Retirer'}
                  </button>
                </div>
                {ouverte === c.id && <CarteMentale enregistree={c.carte} onFermer={() => setOuverte(null)} />}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

/** Entree vers la page a part des cours de sources libres (docs/cours-libres.md). */
function CarteCoursRecuperes() {
  return (
    <Card className="p-[19px]">
      <CardHead titre="Cours récupérés" sousTitre="Cours de sites tiers sous licence libre, rangés par matière" />
      <p className="mt-3 text-[12px] leading-[1.45] text-muted">
        Ils ne sont pas rédigés par Lexia et peuvent contenir des erreurs : à vérifier avec les textes officiels.
      </p>
      <Lien href="/cours-recuperes" className="mt-3 inline-block rounded-[7px] border border-line px-3 py-1.5 text-[12px] text-forest hover:border-[#9eafa3]">
        Voir les cours récupérés
      </Lien>
    </Card>
  )
}

export function VueBibliotheque() {
  return (
    <>
      <EnTete surtitre="Bibliothèque" titre="Annales et ressources." texte="Annales d’examens par matière, manuels à consulter en bibliothèque et sources officielles du corpus." />
      <RechercheBibliotheque />
      {/* Annales d'abord : les sources generales figurent deja sur « Mon espace » (audit du 2026-11-16, point 13). */}
      <div className="grid items-start gap-[18px] tab:grid-cols-2">
        <CarteAnnales />
        <CarteBibliotheque complete />
        <CarteSources />
        <CarteCoursRecuperes />
      </div>
      <p className="mt-4 text-[12px] text-muted">
        Les bibliographies recommandées par les facultés partenaires seront ajoutées ici (métadonnées et liens uniquement).
      </p>
    </>
  )
}
