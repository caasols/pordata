// Fuzzy search over the catalogue, ported verbatim from the original
// vanilla implementation: substring in name (3) > substring anywhere
// (2) > word prefix (1.5) > bounded edit distance (1). Accent-blind.

export interface Row {
  id: number;
  area: string;
  name: string;
  // `name` stays the full PORDATA string (search and sort use it);
  // `title` and `breakdown` are the same string split for display, and
  // `breakdown` is "" whenever build_catalogue refused the split.
  title?: string;
  breakdown?: string;
  unit?: string;
  name_en: string;
  description: string;
  fontes: string[];
  ultima_atualizacao: string;
  url: string;
  harvested_at: string;
  removed?: boolean;
  featured?: string[];
}

export interface PreparedRow extends Row {
  _name: string;
  _hay: string;
  _words: string[];
}

export const norm = (s: string | null | undefined): string =>
  (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

export function prepare(rows: Row[]): PreparedRow[] {
  return rows.map((r) => {
    const hay = norm([r.name, r.name_en, r.description,
      (r.fontes || []).join(" ")].join(" "));
    return {
      ...r,
      _name: norm(r.name),
      _hay: hay,
      _words: hay.split(/[^a-z0-9%€]+/).filter((w) => w.length > 1),
    };
  });
}

export function editDistance(a: string, b: string, max: number): number {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    let rowMin = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      if (cur[j] < rowMin) rowMin = cur[j];
    }
    if (rowMin > max) return max + 1;
    prev = cur;
  }
  return prev[b.length];
}

export function tokenScore(tok: string, r: PreparedRow): number {
  if (r._hay.includes(tok)) return r._name.includes(tok) ? 3 : 2;
  if (tok.length < 3) return 0;
  // (A word-prefix tier existed here historically, but a token that
  // prefixes a word is always a substring of the haystack, so the
  // substring check above already returned - it was dead code.)
  const maxEd = tok.length >= 8 ? 2 : (tok.length >= 5 ? 1 : 0);
  if (!maxEd) return 0;
  for (const w of r._words)
    if (editDistance(tok, w, maxEd) <= maxEd) return 1;
  return 0;
}

// "relevance" (fuzzy-score order) was pulled from the UI 2026-08-23 —
// the score ordering was not useful for browsing; it returns as a real
// blended ranking per roadmap item 9. Match scores still gate which
// rows count as hits.
export type SortMode =
  "az" | "za" | "new" | "old" | "srcFew" | "srcMany" | "random";

export type Hit = [number, PreparedRow];

/**
 * A stable ordering key from a seed and the row's own identity.
 *
 * Not a shuffle of the array: the key depends only on `(seed, area, id)`,
 * so the survivors of a search or a filter keep the order they had. A
 * Fisher-Yates over the filtered list would re-deal the cards on every
 * keystroke, which is the opposite of what a browse order is for. The
 * same seed always gives the same deal, so infinite scroll appends
 * rather than reshuffling; a new seed is dealt only when the reader asks
 * for one by picking Random again.
 *
 * FNV-1a, with `Math.imul` because the 32-bit product overflows a double.
 */
export function shuffleKey(seed: number, r: PreparedRow): number {
  let hash = (seed ^ 0x811c9dc5) >>> 0;
  const id = `${r.area}/${r.id}`;
  for (let i = 0; i < id.length; i++) {
    hash = Math.imul(hash ^ id.charCodeAt(i), 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

/** How many sources the card credits — the `Fontes` column, as shown. */
export function sourceCount(r: PreparedRow): number {
  return (r.fontes || []).length;
}

export function searchAndSort(rows: PreparedRow[], query: string,
    activeAreas: ReadonlySet<string>, sortMode: SortMode,
    primaryName: (r: PreparedRow) => string, lang: string,
    summaryOnly = false, seed = 0): Hit[] {
  const terms = norm(query).split(/\s+/).filter(Boolean);
  const hits: Hit[] = [];
  for (const r of rows) {
    // areas are one axis (OR within it, all when none picked); the
    // summary filter is a separate axis and ANDs with them
    if (activeAreas.size && !activeAreas.has(r.area)) continue;
    if (summaryOnly && !r.featured?.length) continue;
    let score = 1;
    for (const term of terms) {
      const s = tokenScore(term, r);
      if (!s) { score = 0; break; }
      score += s;
    }
    if (score) hits.push([score, r]);
  }
  // Precomputed sort keys + one collator: comparators run ~n log n
  // times per keystroke, so no name derivation or collator construction
  // inside them.
  const collator = new Intl.Collator(lang);
  const names = new Map(hits.map((h) => [h[1], primaryName(h[1]) || ""]));
  const cmpName = (a: Hit, b: Hit) =>
    collator.compare(names.get(a[1])!, names.get(b[1])!);
  const dateOf = (h: Hit) => h[1].ultima_atualizacao || "";
  if (sortMode === "az") hits.sort(cmpName);
  else if (sortMode === "za") hits.sort((a, b) => cmpName(b, a));
  else if (sortMode === "new")   // empty dates compare lowest -> last
    hits.sort((a, b) =>
      dateOf(b).localeCompare(dateOf(a)) || cmpName(a, b));
  else if (sortMode === "old")   // undated entries go last, not first
    hits.sort((a, b) => {
      const da = dateOf(a), db = dateOf(b);
      if (!da || !db) return !da && !db ? cmpName(a, b) : (da ? -1 : 1);
      return da.localeCompare(db) || cmpName(a, b);
    });
  else if (sortMode === "srcFew" || sortMode === "srcMany") {
    // Ties are the common case, not the exception: 1,264 of 2,196 rows
    // credit exactly two sources. So the chain matters more than the
    // primary key — newest first, then name — and it does *not* invert
    // with the direction: asking for the least-sourced indicators is
    // not asking for the oldest of them.
    const counts = new Map(hits.map((h) => [h[1], sourceCount(h[1])]));
    const sign = sortMode === "srcFew" ? 1 : -1;
    hits.sort((a, b) =>
      sign * (counts.get(a[1])! - counts.get(b[1])!)
      || dateOf(b).localeCompare(dateOf(a))
      || cmpName(a, b));
  } else if (sortMode === "random")
    hits.sort((a, b) =>
      shuffleKey(seed, a[1]) - shuffleKey(seed, b[1]) || cmpName(a, b));
  return hits;
}
