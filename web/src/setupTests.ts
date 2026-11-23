import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/react'
import { beforeEach } from 'vitest'

// jsdom n'implemente pas le defilement
Element.prototype.scrollIntoView = () => {}

// jsdom n'implemente pas ResizeObserver (utilise par les graphiques)
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver

// La seance (conversation, questionnaire) vit dans sessionStorage : chaque test repart d'un onglet neuf.
beforeEach(() => sessionStorage.clear())

// findBy et waitFor attendent 1 s par defaut : sur un Mac charge pendant une publication, des tests de depot
// echouaient a 1 030 ms puis passaient seuls (publications du 23/11). 5 s : toujours un echec net si rien n'arrive.
configure({ asyncUtilTimeout: 5000 })
