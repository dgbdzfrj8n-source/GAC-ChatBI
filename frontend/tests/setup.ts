// Vitest setup
import "@testing-library/jest-dom/vitest";

// Mock Next.js dynamic imports (if needed by tests)
// Mock localStorage in jsdom if missing
if (typeof window !== "undefined" && !window.localStorage) {
  const store: Record<string, string> = {};
  Object.defineProperty(window, "localStorage", {
    value: {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = String(v); },
      removeItem: (k: string) => { delete store[k]; },
      clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
    },
  });
}
