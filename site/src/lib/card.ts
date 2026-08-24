// What a result card shows, as pure functions.
//
// These lived in App.tsx, which meant they were unit-tested but never
// mutation-tested: StrykerJS mutates `src/lib` only. Putting App.tsx in
// scope instead scores the JSX — a mutated className or aria attribute
// survives every meaningful test, so the number says little and the
// break threshold has to be lowered to accommodate it. Logic belongs in
// lib, where the 85% threshold already applies; composition stays in the
// component, covered by the integration tests in App.test.tsx.

import type { PreparedRow } from "./search";

/**
 * The card answers "is this the row I meant?", so it shows the title
 * split from its breakdown clause. `breakdown` is Portuguese prose from
 * PORDATA, so it rides with the PT name only — the same rule the
 * description followed before it was dropped.
 */
export function cardParts(r: PreparedRow, lang: string):
    { title: string; coverage: string } {
  if (lang !== "pt" && r.name_en)
    return { title: r.name_en, coverage: "" };
  return { title: r.title || r.name, coverage: r.breakdown || "" };
}

/**
 * "abr 2026", not "2026-04-23": a statistical series is not revised to
 * the day, and the exact date is one click away. Anything that is not an
 * ISO date passes through untouched rather than being guessed at.
 */
export function monthYear(iso: string, lang: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso || "";
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(lang, {
    month: "short", year: "numeric", timeZone: "UTC",
  }).format(d);
}

/**
 * The first source plus a count. The full list belongs on the detail
 * page: "SGMAI - Base de Dados do Recenseamento Eleitoral (eleitores)"
 * and three more is 194 characters the card cannot spend.
 */
export function shortSources(fontes: string[] | undefined): string {
  if (!fontes || !fontes.length) return "";
  const first = fontes[0].split(" - ")[0].trim();
  return fontes.length > 1 ? `${first} +${fontes.length - 1}` : first;
}
