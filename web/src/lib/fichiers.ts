// Fichiers de cours : formats acceptes et lecture d'un glisser-deposer (fichiers ou dossier).

const EXTENSIONS = ['.pdf', '.docx', '.odt', '.pptx', '.txt', '.md']
/** Formats acceptes, en clair, pour les messages du site. */
export const FORMATS_LISIBLES = 'PDF, Word, OpenDocument, PowerPoint ou texte'
/** Valeur de l'attribut accept des champs de fichier : une seule liste pour tout le site. */
export const ACCEPT = EXTENSIONS.join(',')
export const formatAccepte = (f: File) => EXTENSIONS.some((e) => f.name.toLowerCase().endsWith(e))
// Statut « erreur » : le calcul des vecteurs a echoue, le cours reste interrogeable par mots-cles et le
// calcul est relance automatiquement (audit C10). Meme libelle dans la liste des cours et dans leur choix.
export const STATUTS = { traitement: 'en préparation…', pret: 'prêt', erreur: 'mots-clés seulement, nouvel essai bientôt' }
export const sansExtension = (nom: string) => nom.replace(/\.[^.]+$/, '')

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

