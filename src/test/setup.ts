import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom no implementa ResizeObserver (lo usa recharts)
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverStub);

// jsdom no implementa matchMedia (lo usan librerías de UI)
if (!window.matchMedia) {
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  );
}
