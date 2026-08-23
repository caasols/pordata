// Fuzzy search over the catalogue, ported verbatim from the original
// vanilla implementation: substring in name (3) > substring anywhere
// (2) > word prefix (1.5) > bounded edit distance (1). Accent-blind.

export interface Row {
  id: number;
  area: string;
  name: string;
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
  const maxEd = tok.length >= 8 ? 2 : (tok.length >= 5 ? 1 : 0);
  let best = 0;
  for (const w of r._words) {
    if (w.startsWith(tok)) { best = Math.max(best, 1.5); continue; }
    if (maxEd && editDistance(tok, w, maxEd) <= maxEd)
      best = Math.max(best, 1);
    if (best >= 1.5) break;
  }
  return best;
}

export type SortMode = "relevance" | "az" | "za" | "new" | "old";

export type Hit = [number, PreparedRow];

export function searchAndSort(rows: PreparedRow[], query: string,
    activeAreas: ReadonlySet<string>, sortMode: SortMode,
    primaryName: (r: PreparedRow) => string, lang: string): Hit[] {
  const terms = norm(query).split(/\s+/).filter(Boolean);
  const hits: Hit[] = [];
  for (const r of rows) {
    if (activeAreas.size && !activeAreas.has(r.area)) continue;
    let score = 1;
    for (const term of terms) {
      const s = tokenScore(term, r);
      if (!s) { score = 0; break; }
      score += s;
    }
    if (score) hits.push([score, r]);
  }
  hits.sort((a, b) => b[0] - a[0] || a[1].name.localeCompare(b[1].name));
  if (sortMode !== "relevance") {
    const nameOf = (h: Hit) => primaryName(h[1]) || "";
    const cmpName = (a: Hit, b: Hit) =>
      nameOf(a).localeCompare(nameOf(b), lang);
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
  }
  return hits;
}
