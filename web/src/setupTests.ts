import '@testing-library/jest-dom/vitest'

// jsdom n'implemente pas le defilement
Element.prototype.scrollIntoView = () => {}

// jsdom n'implemente pas ResizeObserver (utilise par les graphiques)
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver
