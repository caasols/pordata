// How stale is an indicator? (roadmap 8c)
//
// Deliberately **not** a stored field, where the source organisation is.
// The distinction is that a bucket is relative to *now*: a row built in
// December as "this year" is wrong on 1 January, and the harvest only
// rebuilds rows whose records changed, so the wrong answer would persist
// for as long as PORDATA left that indicator alone. Deriving it in the
// client costs nothing — `ultima_atualizacao` already ships on every
// row — and it cannot rot.
//
// The organisation is the mirror image and is stored: it is a property
// of the row that only a rebuild can change, and normalising 159 strings
// in Python keeps that logic where it is tested and mutation-tested.

export type Recency = "current" | "recent" | "stale" | "";

// Five years is the roadmap's own line ("updated this year / stale >5y").
// It is a judgement about statistics rather than a measurement: an
// annual series untouched for five years has usually been discontinued
// rather than merely not yet refreshed.
export const STALE_YEARS = 5;

/**
 * `current` — updated in the current calendar year.
 * `recent`  — within STALE_YEARS.
 * `stale`   — older, or the series stopped.
 * `""`      — no usable date, which is a third state and not a synonym
 *             for stale: 0 rows lack one today, but a parse regression
 *             upstream would make every row look ancient rather than
 *             unknown.
 */
export function recency(iso: string | undefined, now: Date): Recency {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return "";
  const year = Number(iso.slice(0, 4));
  if (!Number.isFinite(year)) return "";
  const thisYear = now.getUTCFullYear();
  if (year >= thisYear) return "current";
  if (thisYear - year <= STALE_YEARS) return "recent";
  return "stale";
}
