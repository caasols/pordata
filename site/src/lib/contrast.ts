// Contrast arithmetic, so a token pair can be checked instead of eyeballed.
//
// This exists because the guard that was there asserted a ring *string*
// was present and never whether it could be seen: `focus-visible:ring-
// ring/30` computes to 1.29:1 in light theme against WCAG 1.4.11's 3:1,
// and `outline-none` sits unconditionally alongside it — so the focus
// indicator was worse than shipping none at all. The micro-column labels
// (9.5px at 75% opacity) and the `n/a` marker (50%) failed 1.4.3 the
// same way, on the 1,057 rows with no unit.
//
// Kept in src/lib rather than in the test file because that is where
// StrykerJS mutates: a helper living beside the assertion is unit-tested
// but never mutation-tested.

/** One oklch triple, as the theme tokens are written. */
export type Oklch = { l: number; c: number; h: number };

export function parseOklch(value: string): Oklch | null {
  const m = value.match(
    /oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:deg)?\s*\)/i);
  if (!m) return null;
  return { l: Number(m[1]), c: Number(m[2]), h: Number(m[3]) };
}

/** oklch -> linear sRGB, via oklab. */
export function toLinearRgb({ l, c, h }: Oklch): [number, number, number] {
  const rad = (h * Math.PI) / 180;
  const a = c * Math.cos(rad);
  const b = c * Math.sin(rad);
  const l_ = l + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = l - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = l - 0.0894841775 * a - 1.291485548 * b;
  const L = l_ ** 3;
  const M = m_ ** 3;
  const S = s_ ** 3;
  return [
    4.0767416621 * L - 3.3077115913 * M + 0.2309699292 * S,
    -1.2684380046 * L + 2.6097574011 * M - 0.3413193965 * S,
    -0.0041960863 * L - 0.7034186147 * M + 1.707614701 * S,
  ];
}

/** Relative luminance (WCAG 2.x), from linear sRGB. */
export function luminance(rgb: [number, number, number]): number {
  const [r, g, b] = rgb.map((v) => Math.min(1, Math.max(0, v)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Composite `fg` over `bg` at `alpha`, then return the contrast ratio.
 *
 * The alpha matters and is the whole point: every failure here came from
 * a `/30`, `/50` or `/75` modifier on a token that passes at full
 * opacity, so a checker ignoring alpha would have certified all of them.
 */
export function contrast(fg: Oklch, bg: Oklch, alpha = 1): number {
  const f = toLinearRgb(fg);
  const b = toLinearRgb(bg);
  const mixed = f.map((v, i) => v * alpha + b[i] * (1 - alpha)) as
    [number, number, number];
  const [hi, lo] = [luminance(mixed), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** WCAG minimums. Text under 18.66px (or under 24px bold) needs 4.5. */
export const MIN_NON_TEXT = 3;
export const MIN_TEXT = 4.5;
export const LARGE_TEXT_PX = 18.66;

export function required(fontSizePx: number | null): number {
  if (fontSizePx === null) return MIN_NON_TEXT;
  return fontSizePx >= LARGE_TEXT_PX ? MIN_NON_TEXT : MIN_TEXT;
}
