// Fichiers de cours : formats acceptes et lecture d'un glisser-deposer (fichiers ou dossier).

const EXTENSIONS = ['.pdf', '.docx', '.txt', '.md']
export const formatAccepte = (f: File) => EXTENSIONS.some((e) => f.name.toLowerCase().endsWith(e))
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

