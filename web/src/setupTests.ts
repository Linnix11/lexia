import '@testing-library/jest-dom/vitest'

// jsdom n'implemente pas le defilement
Element.prototype.scrollIntoView = () => {}
