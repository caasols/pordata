import { describe, expect, it } from "vitest";

import { formatUnit, unitParts, untranslatedTerms } from "./units";

describe("unitParts", () => {
  it("splits on the compositional separator", () => {
    expect(unitParts("Euro - Milhões")).toEqual(["Euro", "Milhões"]);
    expect(unitParts("Indivíduo")).toEqual(["Indivíduo"]);
  });
  it("trims and drops empties", () => {
    expect(unitParts("Euro -  - Milhões")).toEqual(["Euro", "Milhões"]);
    expect(unitParts("")).toEqual([]);
  });
});

describe("formatUnit", () => {
  it("translates both halves", () => {
    expect(formatUnit("Euro - Milhões", "en")).toBe("Euro - Millions");
    expect(formatUnit("Indivíduo - Milhares", "en"))
      .toBe("Individual - Thousands");
  });
  it("translates a bare measure", () => {
    expect(formatUnit("Indivíduo", "en")).toBe("Individual");
  });
  it("leaves symbols alone", () => {
    expect(formatUnit("Taxa - ‰", "en")).toBe("Rate - ‰");
    expect(formatUnit("Proporção - %", "en")).toBe("Proportion - %");
  });
  it("repairs the lost superscript in Portuguese too", () => {
    // the chart caption drops the sup tag, so "m 3" is wrong in PT
    expect(formatUnit("m 3 - Milhões", "pt")).toBe("m³ - Milhões");
    expect(formatUnit("m 3 - Milhões", "en")).toBe("m³ - Millions");
    expect(formatUnit("t CO 2 eq - Milhares", "pt")).toBe("t CO₂ eq - Milhares");
  });
  it("falls back to Portuguese for an unknown term, never blank", () => {
    expect(formatUnit("Coisa inventada - Milhões", "en"))
      .toBe("Coisa inventada - Millions");
    expect(formatUnit("Totalmente novo", "en")).toBe("Totalmente novo");
  });
  it("a language with no table still gets the PT repairs", () => {
    expect(formatUnit("m 3 - Milhões", "de")).toBe("m³ - Milhões");
    expect(formatUnit("Euro - Milhões", "de")).toBe("Euro - Milhões");
  });
  it("empty in, empty out", () => {
    expect(formatUnit("", "en")).toBe("");
    expect(formatUnit("", "pt")).toBe("");
  });
  it("handles the dual-axis forms PORDATA emits", () => {
    expect(formatUnit("(A) Requerente (B) Titular", "en"))
      .toBe("(A) Applicant (B) Holder");
  });
});

describe("untranslatedTerms", () => {
  it("names only the parts with no entry", () => {
    expect(untranslatedTerms("Coisa inventada - Milhões", "en"))
      .toEqual(["Coisa inventada"]);
    expect(untranslatedTerms("Euro - Milhões", "en")).toEqual([]);
  });
  it("reports every part when the language has no table", () => {
    expect(untranslatedTerms("Euro - Milhões", "de"))
      .toEqual(["Euro", "Milhões"]);
  });
});
