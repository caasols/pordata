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
  it("identical strings cost zero", () => {
    expect(editDistance("igual", "igual", 2)).toBe(0);
  });
});

describe("prepare / tokenScore", () => {
  const r = prepare([row({})])[0];

  it("builds accent-free haystack and words", () => {
    expect(r._name).toBe("taxa de natalidade");
    expect(r._hay).toContain("birth rate");
    expect(r._words).toContain("natalidade");
    expect(r._words).not.toContain("");
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
  it("rejects short unmatched tokens", () => {
    expect(tokenScore("zz", r)).toBe(0);
  });
});

describe("searchAndSort", () => {
  const rows = prepare([
    row({ id: 1, name: "Taxa de natalidade", ultima_atualizacao: "2026-01-01" }),
    row({ id: 2, area: "europa", name: "Índice de Gini",
          name_en: "Gini index", description: "Desigualdade",
          ultima_atualizacao: "2025-05-05" }),
    row({ id: 3, area: "municipios", name: "Médicos",
          name_en: "Doctors", description: "Por mil habitantes",
          ultima_atualizacao: "" }),
  ]);
  const run = (q: string, areas: Set<string>, mode: SortMode) =>
    searchAndSort(rows, q, areas, mode, (r) => r.name, "pt")
      .map((h) => h[1].id);

  it("empty query returns everything", () => {
    expect(run("", new Set(), "az")).toHaveLength(3);
  });
  it("filters by active areas; empty set means all", () => {
    expect(run("", new Set(["europa"]), "az")).toEqual([2]);
    expect(run("", new Set(["europa", "municipios"]), "az"))
      .toEqual([2, 3]);
  });
  it("every term must match", () => {
    expect(run("gini desigualdade", new Set(), "az")).toEqual([2]);
    expect(run("gini natalidade", new Set(), "az")).toEqual([]);
  });
  it("sorts by name both ways", () => {
    expect(run("", new Set(), "az")).toEqual([2, 3, 1]);
    expect(run("", new Set(), "za")).toEqual([1, 3, 2]);
  });
  it("newest first puts undated last", () => {
    expect(run("", new Set(), "new")).toEqual([1, 2, 3]);
  });
  it("oldest first also puts undated last", () => {
    expect(run("", new Set(), "old")).toEqual([2, 1, 3]);
  });
});
