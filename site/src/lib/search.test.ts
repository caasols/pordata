import { describe, expect, it } from "vitest";

import {
  editDistance, norm, prepare, searchAndSort, tokenScore,
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
  const run = (q: string, areas: Set<string>, mode: SortMode) =>
    searchAndSort(rows, q, areas, mode, (r) => r.name, "pt")
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
});
