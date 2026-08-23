// Unit rendering (roadmap 18).
//
// PORDATA writes units compositionally — "<measure> - <scale>", as in
// "Euro - Milhões" or "Taxa - ‰" — so the 148 distinct strings in the
// catalogue are really 108 measures crossed with 14 scales. Translating
// the parts covers the whole vocabulary and any combination PORDATA
// invents later.
//
// The vocabulary lives in unit-terms.json rather than here because
// qa_catalogue.py gates coverage against the same file; two copies would
// drift. An unknown term falls back to Portuguese — the behaviour before
// this existed — so a new PORDATA unit degrades instead of blanking.

import TERMS from "./unit-terms.json";

const TABLES = TERMS as unknown as Record<string, Record<string, string>>;

export const SEPARATOR = " - ";

/** Split a unit into its parts, as the vocabulary is keyed. */
export function unitParts(unit: string): string[] {
  return unit.split(SEPARATOR).map((p) => p.trim()).filter(Boolean);
}

/**
 * Render a unit in `lang`. Portuguese still passes through the table:
 * its entries are repairs, not translations — the chart caption loses
 * superscripts, so "m 3" is wrong in Portuguese too.
 */
export function formatUnit(unit: string, lang: string): string {
  if (!unit) return "";
  const table = TABLES[lang];
  // A language with no table (ES/FR/DE/IT, still greyed out) shows the
  // Portuguese string, repaired where we know better.
  const repair = TABLES.pt || {};
  if (!table) {
    return unitParts(unit).map((p) => repair[p] ?? p).join(SEPARATOR);
  }
  return unitParts(unit)
    .map((p) => table[p] ?? repair[p] ?? p)
    .join(SEPARATOR);
}

/** Terms with no entry in `lang` — what a coverage check reports. */
export function untranslatedTerms(unit: string, lang: string): string[] {
  const table = TABLES[lang];
  if (!table) return unitParts(unit);
  return unitParts(unit).filter((p) => !(p in table));
}
