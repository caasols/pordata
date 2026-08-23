import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ALL_LANGS, AREA_LABELS, AVAILABLE, STRINGS, initialLang, translate,
} from "./i18n";

describe("translate", () => {
  it("substitutes params and link placeholders", () => {
    const s = translate("pt", "intro", { n: "2.195" });
    expect(s).toContain("2.195");
    expect(s).toContain('href="https://www.pordata.pt"');
    expect(s).not.toContain("{n}");
    expect(s).not.toContain("{pordata}");
  });
  it("replaces every occurrence of a placeholder", () => {
    const s = translate("en", "foot");
    expect(s).not.toMatch(/\{(repo|json|csv|pordata)\}/);
  });
  it("falls back to pt for unknown language", () => {
    expect(translate("xx", "results", { n: "5" }))
      .toBe("5 indicadores");
  });
  it("falls back to the key for unknown key", () => {
    expect(translate("pt", "nope")).toBe("nope");
  });
});

describe("language tables", () => {
  it("all six UI languages carry the same keys", () => {
    const ptKeys = Object.keys(STRINGS.pt).sort();
    for (const lang of Object.keys(STRINGS))
      expect(Object.keys(STRINGS[lang]).sort()).toEqual(ptKeys);
  });
  it("area labels exist for every UI language", () => {
    for (const area of Object.keys(AREA_LABELS))
      for (const lang of Object.keys(STRINGS))
        expect(AREA_LABELS[area][lang]).toBeTruthy();
  });
  it("lists all 24 EU languages, available ones included", () => {
    expect(ALL_LANGS).toHaveLength(24);
    const codes = new Set(ALL_LANGS.map(([l]) => l));
    expect(codes.size).toBe(24); // codes unique
    for (const l of AVAILABLE) expect(codes.has(l)).toBe(true);
    for (const [l, name] of ALL_LANGS) {
      expect(l).toMatch(/^[a-z]{2}$/);
      expect(name.length).toBeGreaterThan(1);
    }
  });
});

describe("initialLang", () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("honours a stored available language", () => {
    localStorage.setItem("lang", "pt");
    expect(initialLang()).toBe("pt");
  });
  it("ignores a stored unavailable language", () => {
    localStorage.setItem("lang", "fr");
    vi.stubGlobal("navigator", { language: "fr-FR" });
    expect(initialLang()).toBe("en");
  });
  it("uses the browser language when available", () => {
    vi.stubGlobal("navigator", { language: "pt-PT" });
    expect(initialLang()).toBe("pt");
  });
  it("defaults to en otherwise", () => {
    vi.stubGlobal("navigator", { language: "de-DE" });
    expect(initialLang()).toBe("en");
  });
});
