import { describe, expect, it } from "vitest";

import { cardParts, monthYear, shortSources, detailHref } from "./card";
import { prepare, type Row } from "./search";

// A card row with the fields the build now emits. `title` and
// `breakdown` are the full name split at a colon, and are absent
// whenever build_catalogue refused the split.
function baseRow(over: Partial<Row> = {}): Row {
  return {
    id: 1, area: "portugal", name: "N: total e por sexo",
    title: "N", breakdown: "total e por sexo", unit: "Indivíduo",
    name_en: "N en", description: "", fontes: [],
    ultima_atualizacao: "", url: "u", harvested_at: "", ...over,
  };
}

const prepared = (over: Partial<Row> = {}) => prepare([baseRow(over)])[0];

describe("cardParts", () => {

  it("PT shows the split title and its breakdown", () => {
    expect(cardParts(prepared({}), "pt"))
      .toEqual({ title: "N", coverage: "total e por sexo" });
  });
  it("falls back to the full name when the split was refused", () => {
    expect(cardParts(prepared({ title: "", breakdown: "" }), "pt"))
      .toEqual({ title: "N: total e por sexo", coverage: "" });
  });
  it("other languages show the EN name and no PT breakdown", () => {
    expect(cardParts(prepared({}), "en"))
      .toEqual({ title: "N en", coverage: "" });
  });
  it("missing EN name falls back to the PT split", () => {
    expect(cardParts(prepared({ name_en: "" }), "en"))
      .toEqual({ title: "N", coverage: "total e por sexo" });
  });
});

describe("monthYear", () => {
  it("renders month precision", () => {
    expect(monthYear("2026-04-23", "en")).toBe("Apr 2026");
  });
  it("localizes the month", () => {
    expect(monthYear("2026-04-23", "pt")).toMatch(/2026/);
    expect(monthYear("2026-04-23", "pt")).not.toBe("Apr 2026");
  });
  it("does not drift across the UTC day boundary", () => {
    expect(monthYear("2026-01-01", "en")).toBe("Jan 2026");
    expect(monthYear("2026-12-31", "en")).toBe("Dec 2026");
  });
  it("passes through anything that is not an ISO date", () => {
    expect(monthYear("", "en")).toBe("");
    expect(monthYear("2026-04", "en")).toBe("2026-04");
    expect(monthYear("not a date", "en")).toBe("not a date");
  });
  it("returns the input for a well-shaped but unreal date", () => {
    expect(monthYear("2026-13-45", "en")).toBe("2026-13-45");
  });
});

describe("shortSources", () => {
  it("returns a lone source unchanged", () => {
    expect(shortSources(["INE"])).toBe("INE");
  });
  it("appends a count for the rest", () => {
    expect(shortSources(["INE", "PORDATA"])).toBe("INE +1");
    expect(shortSources(["INE", "PORDATA", "DGEEC"])).toBe("INE +2");
  });
  it("keeps only the entity before a dash gloss", () => {
    expect(shortSources(["SGMAI - Base de Dados do Recenseamento Eleitoral"]))
      .toBe("SGMAI");
  });
  it("handles empty and missing", () => {
    expect(shortSources([])).toBe("");
    expect(shortSources(undefined)).toBe("");
  });
});

describe("detailHref", () => {
  it("points at this project's own page, not pordata.pt", () => {
    expect(detailHref({ area: "portugal", id: 42 })).toBe("indicador/portugal/42/");
  });

  it("is relative, because the site lives on a project subpath", () => {
    // an absolute "/indicador/..." resolves against caasols.github.io,
    // not caasols.github.io/pordata, and 404s
    expect(detailHref({ area: "europa", id: 1 }).startsWith("/")).toBe(false);
  });

  it("keeps the area in the path, because ids repeat across areas", () => {
    expect(detailHref({ area: "portugal", id: 1 }))
      .not.toBe(detailHref({ area: "municipios", id: 1 }));
  });

  it("ends in a slash so the static index.html is served", () => {
    expect(detailHref({ area: "municipios", id: 858 })).toMatch(/\/$/);
  });
});
