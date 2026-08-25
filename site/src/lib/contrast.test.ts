import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  parseOklch, contrast, toLinearRgb, luminance, required,
  MIN_NON_TEXT, MIN_TEXT,
} from "./contrast";

// The tokens as shipped, read from the stylesheet rather than restated:
// a copy here would pass while the site failed.


const CSS = readFileSync(resolve(process.cwd(), "src/index.css"), "utf8");

function tokens(selector: string): Record<string, string> {
  const start = CSS.indexOf(selector);
  const open = CSS.indexOf("{", start);
  const close = CSS.indexOf("}", open);
  const out: Record<string, string> = {};
  for (const line of CSS.slice(open + 1, close).split("\n")) {
    const m = line.match(/--([\w-]+):\s*([^;]+);/);
    if (m) out[m[1]] = m[2].trim();
  }
  return out;
}

const LIGHT = tokens(":root {");
const DARK = tokens(".dark {");

function ratio(theme: Record<string, string>, fg: string, bg: string, alpha = 1) {
  const f = parseOklch(theme[fg]);
  const b = parseOklch(theme[bg]);
  expect(f, `${fg} missing or not oklch`).not.toBeNull();
  expect(b, `${bg} missing or not oklch`).not.toBeNull();
  return contrast(f!, b!, alpha);
}

describe("contrast arithmetic", () => {
  // Anchored to exact values, not thresholds. The oklch->sRGB matrix is
  // fifteen coefficients, and a check that only asks "is this over 3"
  // passes with any of them slightly wrong — so the arithmetic gets
  // pinned where the answer is known independently.
  it("puts white on black at exactly 21, the WCAG maximum", () => {
    const white = parseOklch("oklch(1 0 0)")!;
    const black = parseOklch("oklch(0 0 0)")!;
    expect(contrast(white, black)).toBeCloseTo(21, 6);
    expect(contrast(black, white)).toBeCloseTo(21, 6);
  });

  it("maps white and black to the ends of linear sRGB", () => {
    expect(toLinearRgb(parseOklch("oklch(1 0 0)")!)
      .map((v) => Math.round(v * 1e6) / 1e6)).toEqual([1, 1, 1]);
    expect(luminance(toLinearRgb(parseOklch("oklch(0 0 0)")!))).toBeCloseTo(0, 9);
  });

  it("is symmetric in its arguments", () => {
    const a = parseOklch(LIGHT["muted-foreground"])!;
    const b = parseOklch(LIGHT["background"])!;
    expect(contrast(a, b)).toBeCloseTo(contrast(b, a), 9);
  });

  it("reproduces the measured value for a real token pair", () => {
    // muted-foreground on white, computed independently at 4.81.
    expect(ratio(LIGHT, "muted-foreground", "background")).toBeCloseTo(4.807, 2);
  });

  it("returns 1 for a colour against itself", () => {
    expect(ratio(LIGHT, "background", "background")).toBeCloseTo(1, 9);
  });

  it("rejects a value that is not oklch", () => {
    expect(parseOklch("#ffffff")).toBeNull();
    expect(parseOklch("var(--background)")).toBeNull();
  });

  it("parses the three components in order", () => {
    expect(parseOklch("oklch(0.5 0.1 200)")).toEqual({ l: 0.5, c: 0.1, h: 200 });
  });

  it("reads hue as degrees around the circle", () => {
    const a = toLinearRgb({ l: 0.6, c: 0.15, h: 30 });
    const b = toLinearRgb({ l: 0.6, c: 0.15, h: 210 });
    expect(a[0]).toBeGreaterThan(b[0]);   // 30deg is red-ward
    expect(b[2]).toBeGreaterThan(a[2]);   // 210deg is blue-ward
  });

  it("weights green most and blue least, as sRGB luminance does", () => {
    const red = luminance([1, 0, 0]);
    const green = luminance([0, 1, 0]);
    const blue = luminance([0, 0, 1]);
    expect(green).toBeGreaterThan(red);
    expect(red).toBeGreaterThan(blue);
    expect(red + green + blue).toBeCloseTo(1, 9);
  });

  it("clamps a colour that falls outside the sRGB gamut", () => {
    // oklch describes colours sRGB cannot show; an unclamped channel
    // would push luminance past 1 and understate the ratio.
    expect(luminance([1.4, -0.2, 0.5])).toBeLessThanOrEqual(1);
    expect(luminance([1.4, -0.2, 0.5])).toBeGreaterThanOrEqual(0);
  });

  it("treats alpha as part of the colour", () => {
    const solid = ratio(LIGHT, "muted-foreground", "background", 1);
    const faded = ratio(LIGHT, "muted-foreground", "background", 0.5);
    expect(faded).toBeLessThan(solid);
  });

  it("asks 4.5 of small text and 3 of large", () => {
    expect(required(11)).toBe(MIN_TEXT);
    expect(required(24)).toBe(MIN_NON_TEXT);
    expect(required(null)).toBe(MIN_NON_TEXT);
  });
});

// Each row is a real pair the site renders. The `alpha` column is where
// every failure lived: all of these tokens pass at full opacity, so a
// check that ignored the /30, /50 and /75 modifiers would have
// certified the lot.
const PAIRS: Array<{
  what: string; fg: string; bg: string; alpha: number; px: number | null;
}> = [
  // alpha and px are as the components actually ship them, so this table
  // is a description of the site and not of an intention.
  { what: "focus ring on the page (button.tsx, input.tsx, App.tsx)",
    fg: "ring", bg: "background", alpha: 1, px: null },
  { what: "focus ring on a card",
    fg: "ring", bg: "card", alpha: 1, px: null },
  { what: "body text", fg: "foreground", bg: "background", alpha: 1, px: 16 },
  { what: "card text", fg: "card-foreground", bg: "card", alpha: 1, px: 16 },
  { what: "micro-column label (App.tsx Meta)",
    fg: "muted-foreground", bg: "card", alpha: 1, px: 11 },
  { what: "n/a marker on a row with no unit",
    fg: "muted-foreground", bg: "card", alpha: 1, px: 11 },
  { what: "muted body text",
    fg: "muted-foreground", bg: "background", alpha: 1, px: 14 },
  { what: "chart-slot caption",
    fg: "muted-foreground", bg: "background", alpha: 1, px: 14 },
];

describe.each([
  ["light", LIGHT],
  ["dark", DARK],
])("%s theme meets WCAG", (_name, theme) => {
  it.each(PAIRS)("$what", ({ fg, bg, alpha, px }) => {
    const r = ratio(theme, fg, bg, alpha);
    expect(r).toBeGreaterThanOrEqual(required(px));
  });
});
