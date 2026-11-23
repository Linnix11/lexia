// Fichiers de cours : formats acceptes et lecture d'un glisser-deposer (fichiers ou dossier).

const EXTENSIONS = ['.pdf', '.docx', '.odt', '.pptx', '.rtf', '.txt', '.md', '.jpg', '.jpeg', '.png']
/** Formats acceptes, en clair, pour les messages du site. */
export const FORMATS_LISIBLES = 'PDF (même scanné), Word, OpenDocument, PowerPoint, RTF, texte ou photo (JPEG, PNG)'
/** Taille maximale d'un fichier, verifiee aussi par le serveur (api/cours.py). */
export const TAILLE_MAX = 20 * 1024 * 1024
/** Valeur de l'attribut accept des champs de fichier : une seule liste pour tout le site. */
export const ACCEPT = EXTENSIONS.join(',')
export const formatAccepte = (f: File) => EXTENSIONS.some((e) => f.name.toLowerCase().endsWith(e))
// Statut « erreur » : le calcul des vecteurs a echoue, le cours reste interrogeable par mots-cles et le
// calcul est relance automatiquement (audit C10). Meme libelle dans la liste des cours et dans leur choix.
export const STATUTS = { traitement: 'en préparation…', pret: 'prêt', erreur: 'mots-clés seulement, nouvel essai bientôt' }
export const sansExtension = (nom: string) => nom.replace(/\.[^.]+$/, '')

/** Titres des cours deposes ensemble : le nom sans extension, suivi du format quand deux fichiers portent le meme
 * nom, puis d'un numero si besoin. Trois « cours-contrats » se confondaient (recette du 2026-11-20, D-10). */
export function titresDistincts(noms: string[]): string[] {
  const cle = (t: string) => t.toLocaleLowerCase('fr')
  const bases = noms.map(sansExtension)
  const nombre = new Map<string, number>()
  for (const b of bases) nombre.set(cle(b), (nombre.get(cle(b)) ?? 0) + 1)
  const titres = noms.map((nom, i) => {
    const ext = /\.([^.]+)$/.exec(nom)?.[1]
    return (nombre.get(cle(bases[i])) ?? 0) > 1 && ext ? `${bases[i]} (${ext.toUpperCase()})` : bases[i]
  })
  const vus = new Map<string, number>()
  return titres.map((t) => {
    const n = (vus.get(cle(t)) ?? 0) + 1
    vus.set(cle(t), n)
    return n > 1 ? `${t} ${n}` : t
  })
}

/** Refus d'un fichier avant l'envoi (format, taille, fichier vide), en clair ; null s'il peut partir. */
export function refusFichier(f: File): string | null {
  if (!formatAccepte(f)) {
    const ext = /\.[^.]+$/.exec(f.name)?.[0]
    if (ext === '.doc') return 'ancien format Word (.doc) : ouvrez-le puis enregistrez-le en .docx.'
    if (ext === '.heic' || ext === '.heif') return 'photo HEIC : enregistrez-la en JPEG (ou réglez l’appareil sur « Le plus compatible »).'
    return `format non pris en charge (${ext ?? 'sans extension'}) : ${FORMATS_LISIBLES}.`
  }
  if (f.size === 0) return 'le fichier est vide.'
  if (f.size > TAILLE_MAX) return `fichier trop volumineux (${(f.size / 1024 / 1024).toFixed(1).replace('.', ',')} Mo, 20 Mo au plus).`
  return null
}

/** Fichiers deposes par glisser-deposer, y compris le contenu d'un dossier (un niveau de sous-dossiers suffit en pratique). */
export async function fichiersDeposes(dt: DataTransfer): Promise<File[]> {
  const entrees = [...dt.items].map((i) => (i.kind === 'file' ? i.webkitGetAsEntry?.() : null)).filter(Boolean) as FileSystemEntry[]
  if (!entrees.some((e) => e.isDirectory)) return [...dt.files]
  const out: File[] = []
  const lire = async (e: FileSystemEntry, profondeur: number): Promise<void> => {
    if (e.isFile) {
      out.push(await new Promise<File>((ok, ko) => (e as FileSystemFileEntry).file(ok, ko)))
    } else if (e.isDirectory && profondeur < 3) {
      const lecteur = (e as FileSystemDirectoryEntry).createReader()
      let lot: FileSystemEntry[]
      do {
        lot = await new Promise<FileSystemEntry[]>((ok, ko) => lecteur.readEntries(ok, ko))
        for (const x of lot) await lire(x, profondeur + 1)
      } while (lot.length > 0)
    }
  }
  for (const e of entrees) await lire(e, 0)
  return out
}

