import { describe, it, expect, beforeEach, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { initialLang, AVAILABLE } from "./i18n";

// The order is a contract with a second implementation: the 2,196
// pre-rendered pages run their own nine-line copy in
// `scripts/build_detail_pages.py BOOT`, because they ship no bundle.
// Both are pinned here so they cannot drift — which they had, in the
// direction that mattered: BOOT read localStorage only, so a first-time
// English visitor got English on the index and Portuguese on every
// crawlable page.
const CASES: Array<{
  what: string; query?: string; stored?: string; nav: string; want: string;
}> = [
  { what: "query wins over everything", query: "en", stored: "pt",
    nav: "pt-PT", want: "en" },
  { what: "query wins the other way", query: "pt", stored: "en",
    nav: "en-US", want: "pt" },
  { what: "an unavailable query is ignored", query: "de", stored: "en",
    nav: "pt-PT", want: "en" },
  { what: "a stored choice beats the browser", stored: "pt", nav: "en-US",
    want: "pt" },
  { what: "the browser decides when nothing is stored", nav: "pt-BR",
    want: "pt" },
  { what: "an unsupported browser language falls back to English",
    nav: "de-DE", want: "en" },
  { what: "English is the fallback, not Portuguese", nav: "ja-JP",
    want: "en" },
];

describe("initialLang", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  it.each(CASES)("$what", ({ query, stored, nav, want }) => {
    if (stored) localStorage.setItem("lang", stored);
    if (query) window.history.replaceState({}, "", `/?lang=${query}`);
    vi.spyOn(navigator, "language", "get").mockReturnValue(nav);
    expect(initialLang()).toBe(want);
  });

  it("only ever returns a language the site actually has", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("de-DE");
    expect(AVAILABLE.has(initialLang())).toBe(true);
  });

  it("survives localStorage throwing, as it does in private mode", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(navigator, "language", "get").mockReturnValue("pt-PT");
    expect(initialLang()).toBe("pt");
  });
});

describe("the pre-rendered pages implement the same order", () => {
  const BOOT = readFileSync(
    resolve(process.cwd(), "../scripts/build_detail_pages.py"), "utf8");

  it.each([
    ['reads the query parameter', 'get("lang")'],
    ['reads the stored choice', 'localStorage.getItem("lang")'],
    ['reads the browser language', "navigator.language"],
  ])("%s", (_what, needle) => {
    expect(BOOT).toContain(needle);
  });

  it("consults the query before the stored choice", () => {
    const boot = BOOT.slice(BOOT.indexOf("BOOT = ("));
    expect(boot.indexOf("q||l")).toBeGreaterThan(-1);
  });
});

describe("every advertised locale has an address", () => {
  const INDEX = readFileSync(resolve(process.cwd(), "index.html"), "utf8");

  it("declares an alternate for each og:locale:alternate", () => {
    for (const m of INDEX.matchAll(
      /og:locale:alternate"\s+content="(\w\w)_/g)) {
      expect(INDEX).toMatch(
        new RegExp(`rel="alternate" hreflang="${m[1]}"`));
    }
  });

  it("declares an x-default", () => {
    expect(INDEX).toContain('hreflang="x-default"');
  });

  it("names only languages the site has", () => {
    for (const m of INDEX.matchAll(/hreflang="([a-z-]+)"/g)) {
      const base = m[1].split("-")[0];
      if (base === "x") continue;
      expect(AVAILABLE.has(base), `hreflang ${m[1]} is not available`)
        .toBe(true);
    }
  });
});
