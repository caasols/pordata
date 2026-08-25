import { describe, expect, it } from "vitest";

import {
  editDistance, norm, prepare, searchAndSort, shuffleKey,
  sourceCount, tokenScore,
  type Row, type SortMode,
} from "./search";

function row(over: Partial<Row>): Row {
  return {
    id: 1, area: "portugal", name: "Taxa de natalidade",
    name_en: "Birth rate", description: "Nados-vivos por mil habitantes",
    fontes: ["INE", "PORDATA"], ultima_atualizacao: "2026-06-01",
    url: "https://www.pordata.pt/portugal/taxa-1",
    harvested_at: "2026-08-22", ...over,
  };
}

describe("norm", () => {
  it("lowercases and strips accents", () => {
    expect(norm("População Média")).toBe("populacao media");
  });
  it("handles null/undefined", () => {
    expect(norm(null)).toBe("");
    expect(norm(undefined)).toBe("");
  });
});

describe("editDistance", () => {
  it("counts single edits", () => {
    expect(editDistance("gato", "gado", 2)).toBe(1);
    expect(editDistance("casa", "casas", 2)).toBe(1);
  });
  it("returns max+1 when the band is exceeded", () => {
    expect(editDistance("abcdefgh", "zzzzzzzz", 2)).toBe(3);
    expect(editDistance("ab", "abcdef", 2)).toBe(3); // length gap prunes
  });
  it("length gap exactly max still computes", () => {
    expect(editDistance("ab", "abcd", 2)).toBe(2);
  });
  it("identical strings cost zero", () => {
    expect(editDistance("igual", "igual", 2)).toBe(0);
  });
});

describe("prepare / tokenScore", () => {
  const r = prepare([row({})])[0];

  it("builds accent-free haystack and words", () => {
    expect(r._name).toBe("taxa de natalidade");
    expect(r._hay).toContain("birth rate");
    expect(r._hay).toContain("ine pordata");  // fontes are searchable
    expect(r._words).toContain("natalidade");
    expect(r._words).not.toContain("");
  });
  it("drops single-character words", () => {
    const one = prepare([row({ name: "Taxa e renda" })])[0];
    expect(one._words).not.toContain("e");
    expect(one._words).toContain("renda");
  });
  it("tolerates records without fontes", () => {
    const bare = prepare([row({ fontes: undefined as unknown as string[] })]);
    expect(bare[0]._hay).toContain("taxa");
  });
  it("scores name substring highest", () => {
    expect(tokenScore("natalidade", r)).toBe(3);
  });
  it("scores non-name substring lower", () => {
    expect(tokenScore("birth", r)).toBe(2);
  });
  it("scores word prefix", () => {
    expect(tokenScore("natali", r)).toBe(3); // substring of name still
    expect(tokenScore("habit", r)).toBe(2);  // substring of description
    const only = prepare([row({ name: "Emprego", name_en: "",
      description: "", fontes: [] })])[0];
    expect(tokenScore("empre", only)).toBe(3);
    expect(tokenScore("emp", only)).toBe(3);
  });
  it("tolerates typos via bounded edit distance", () => {
    expect(tokenScore("nataildade", r)).toBe(1);
  });
  it("typo budget scales with token length", () => {
    const w = prepare([row({ name: "Abcdefgh abcde", name_en: "",
      description: "", fontes: [] })])[0];
    expect(tokenScore("abcdefxy", w)).toBe(1);  // 8 chars: 2 edits ok
    expect(tokenScore("abcdx", w)).toBe(1);     // 5 chars: 1 edit ok
    expect(tokenScore("abcxy", w)).toBe(0);     // 5 chars: 2 edits not
    expect(tokenScore("abcx", w)).toBe(0);      // 4 chars: no typo budget
  });
  it("rejects short unmatched tokens", () => {
    expect(tokenScore("zz", r)).toBe(0);
  });
});

describe("searchAndSort", () => {
  // Insertion order deliberately differs from every sorted order, so a
  // mutant that skips sorting cannot pass by accident. Ids 2 and 4
  // share a date (tie -> name); 3 and 5 are undated (always last).
  const rows = prepare([
    row({ id: 3, area: "municipios", name: "Médicos",
          name_en: "Doctors", description: "Por mil habitantes",
          ultima_atualizacao: "" }),
    row({ id: 2, area: "europa", name: "Índice de Gini",
          name_en: "Gini index", description: "Desigualdade",
          ultima_atualizacao: "2025-05-05" }),
    row({ id: 5, area: "europa", name: "Zona euro",
          name_en: "Euro area", description: "",
          ultima_atualizacao: "" }),
    row({ id: 1, name: "Taxa de natalidade",
          ultima_atualizacao: "2026-01-01" }),
    row({ id: 4, name: "Empregados",
          ultima_atualizacao: "2025-05-05" }),
  ]);
  const run = (q: string, areas: Set<string>, mode: SortMode,
               summaryOnly = false) =>
    searchAndSort(rows, q, areas, mode, (r) => r.name, "pt", summaryOnly)
      .map((h) => h[1].id);

  it("empty query returns everything", () => {
    expect(run("", new Set(), "az")).toHaveLength(5);
  });
  it("filters by active areas; empty set means all", () => {
    expect(run("", new Set(["europa"]), "az")).toEqual([2, 5]);
    expect(run("", new Set(["europa", "municipios"]), "az"))
      .toEqual([2, 3, 5]);
  });
  it("every term must match", () => {
    expect(run("gini desigualdade", new Set(), "az")).toEqual([2]);
    expect(run("gini natalidade", new Set(), "az")).toEqual([]);
  });
  it("sorts by name both ways", () => {
    expect(run("", new Set(), "az")).toEqual([4, 2, 3, 1, 5]);
    expect(run("", new Set(), "za")).toEqual([5, 1, 3, 2, 4]);
  });
  it("newest first: date desc, ties by name, undated last by name", () => {
    expect(run("", new Set(), "new")).toEqual([1, 4, 2, 3, 5]);
  });
  it("oldest first: date asc, ties by name, undated still last", () => {
    expect(run("", new Set(), "old")).toEqual([4, 2, 1, 3, 5]);
  });
  it("summary filter keeps only flagged rows and ANDs with areas", () => {
    const flagged = prepare([
      row({ id: 7, name: "Com resumo", featured: ["quadro_resumo"] }),
      row({ id: 8, name: "Sem resumo" }),
      row({ id: 9, area: "europa", name: "Europa com resumo",
            featured: ["quadro_resumo"] }),
    ]);
    const pick = (areas: Set<string>, summary: boolean) =>
      searchAndSort(flagged, "", areas, "az", (r) => r.name, "pt", summary)
        .map((h) => h[1].id);
    expect(pick(new Set(), false)).toEqual([7, 9, 8]);  // A-Z by name
    expect(pick(new Set(), true)).toEqual([7, 9]);
    expect(pick(new Set(["europa"]), true)).toEqual([9]);
    expect(pick(new Set(["municipios"]), true)).toEqual([]);
  });
  it("an empty featured array does not count as flagged", () => {
    const edge = prepare([row({ id: 1, name: "A", featured: [] })]);
    expect(searchAndSort(edge, "", new Set(), "az", (r) => r.name, "pt", true))
      .toEqual([]);
  });

});

describe("sorting by how many sources a card credits", () => {
  // Ties are the common case in the real catalogue — 1,264 of 2,196 rows
  // credit exactly two sources — so these fixtures are mostly ties, and
  // the chain is what the tests are about.
  const rows = prepare([
    row({ id: 1, name: "Bravo", fontes: ["INE", "PORDATA"],
          ultima_atualizacao: "2025-01-01" }),
    row({ id: 2, name: "Alfa", fontes: ["INE", "PORDATA"],
          ultima_atualizacao: "2025-01-01" }),
    row({ id: 3, name: "Charlie", fontes: ["INE", "PORDATA"],
          ultima_atualizacao: "2026-01-01" }),
    row({ id: 4, name: "Delta", fontes: ["PORDATA"],
          ultima_atualizacao: "2024-01-01" }),
    row({ id: 5, name: "Echo",
          fontes: ["INE", "Eurostat", "OCDE", "PORDATA"],
          ultima_atualizacao: "2020-01-01" }),
  ]);
  const run = (mode: SortMode) =>
    searchAndSort(rows, "", new Set(), mode, (r) => r.name, "pt")
      .map((h) => h[1].id);

  it("fewest first puts the one-source row at the top", () => {
    expect(run("srcFew")[0]).toBe(4);
  });

  it("most first puts the four-source row at the top", () => {
    expect(run("srcMany")[0]).toBe(5);
  });

  it("breaks a tie on the more recent date", () => {
    // 1, 2 and 3 all credit two sources; 3 is a year newer.
    expect(run("srcFew").slice(1, 2)).toEqual([3]);
    expect(run("srcMany").slice(1, 2)).toEqual([3]);
  });

  it("breaks a same-date tie alphabetically", () => {
    // 1 "Bravo" and 2 "Alfa" share both count and date.
    expect(run("srcFew").slice(2, 4)).toEqual([2, 1]);
  });

  it("does not invert the tie-break with the direction", () => {
    // Asking for the least-sourced indicators is not asking for the
    // oldest of them: both directions resolve ties newest-first.
    const few = run("srcFew"), many = run("srcMany");
    expect(few.indexOf(3)).toBeLessThan(few.indexOf(2));
    expect(many.indexOf(3)).toBeLessThan(many.indexOf(2));
  });

  it("is the exact reverse of itself only on the primary key", () => {
    expect(run("srcFew")[0]).toBe(4);
    expect(run("srcMany").at(-1)).toBe(4);
  });

  it("counts the sources the card shows", () => {
    expect(sourceCount(rows.find((r) => r.id === 5)!)).toBe(4);
  });

  it("treats a row with no sources as the fewest", () => {
    const none = prepare([
      row({ id: 9, name: "Zulu", fontes: [] }),
      row({ id: 8, name: "Yankee", fontes: ["INE"] }),
    ]);
    expect(searchAndSort(none, "", new Set(), "srcFew",
                         (r) => r.name, "pt").map((h) => h[1].id))
      .toEqual([9, 8]);
  });
});

describe("random order", () => {
  const rows = prepare(
    Array.from({ length: 40 }, (_, i) =>
      row({ id: i + 1, name: `Row ${String(i).padStart(2, "0")}` })));
  const run = (seed: number, subset = rows) =>
    searchAndSort(subset, "", new Set(), "random", (r) => r.name, "pt",
                  false, seed).map((h) => h[1].id);

  it("is stable for a given seed", () => {
    expect(run(7)).toEqual(run(7));
  });

  it("deals differently for a different seed", () => {
    expect(run(7)).not.toEqual(run(8));
  });

  it("is not the insertion order", () => {
    expect(run(7)).not.toEqual(rows.map((r) => r.id));
  });

  it("keeps every row exactly once", () => {
    const got = run(7);
    expect(new Set(got).size).toBe(rows.length);
  });

  it("does not re-deal when the list is filtered", () => {
    // The point of hashing identity rather than shuffling the array: a
    // keystroke must not re-order the cards that survive it.
    const full = run(7);
    const half = rows.filter((r) => r.id % 2 === 0);
    const kept = full.filter((id) => id % 2 === 0);
    expect(run(7, half)).toEqual(kept);
  });

  it("gives the same row the same key under the same seed", () => {
    const r = rows[0];
    expect(shuffleKey(3, r)).toBe(shuffleKey(3, r));
    expect(shuffleKey(3, r)).not.toBe(shuffleKey(4, r));
  });

  it("distinguishes rows that share an id across areas", () => {
    // (area, id) is the catalogue key; id alone is not unique.
    const a = prepare([row({ id: 1, area: "portugal", name: "x" })])[0];
    const b = prepare([row({ id: 1, area: "europa", name: "x" })])[0];
    expect(shuffleKey(5, a)).not.toBe(shuffleKey(5, b));
  });

  it("spreads keys rather than clustering them", () => {
    const keys = rows.map((r) => shuffleKey(11, r));
    expect(new Set(keys).size).toBe(rows.length);
  });
});
