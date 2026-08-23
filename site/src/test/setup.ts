import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// with vitest globals off, testing-library cannot self-register cleanup
afterEach(cleanup);

// jsdom lacks the observer APIs the app and Radix rely on. Plain
// assignments (not vi.stubGlobal) so tests calling unstubAllGlobals
// for their own stubs do not lose these.
class ObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
}
(globalThis as any).IntersectionObserver = ObserverStub;
(globalThis as any).ResizeObserver = ObserverStub;

(globalThis as any).matchMedia = (query: string) => ({
  matches: false, media: query, onchange: null,
  addEventListener: () => {}, removeEventListener: () => {},
  addListener: () => {}, removeListener: () => {},
  dispatchEvent: () => false,
});

// Radix menus call pointer-capture and scroll APIs jsdom doesn't have
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => {});
Element.prototype.hasPointerCapture =
  Element.prototype.hasPointerCapture || (() => false);
Element.prototype.setPointerCapture =
  Element.prototype.setPointerCapture || (() => {});
Element.prototype.releasePointerCapture =
  Element.prototype.releasePointerCapture || (() => {});
