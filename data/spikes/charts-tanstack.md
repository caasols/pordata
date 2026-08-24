# Spike: is TanStack Charts the right chart layer? (roadmap 15/14)

Owner question, 2026-08-24: *"can we use tanstack charts? … we need this to be
visually compelling and lightweight."* Measured rather than judged from
reputation. Reproduce with the commands at the bottom;
`charts-tanstack-probe.mjs` is the exact script.

## What was measured

**Package**, from the npm registry:

| | |
|---|---|
| name | `@tanstack/charts` (`@tanstack/react-charts` is now a compat shim pointing here) |
| version | **0.14.0**, published 2026-08-15 |
| release cadence | 0.9.0 → 0.14.0 between **9 and 15 August 2026** — six releases in six days |
| `sideEffects` | `false` |
| export paths | **113**, one per mark and scale (`./line`, `./area`, `./scales/linear`, …) |
| unpacked | 2.7 MB / 559 files — the whole thing, including Angular, Alpine, Vue, React Native adapters |

**Bundle cost**, built with this project's own Vite 7 / React 19 versions,
esbuild-minified, gzipped — a 195-point three-series line chart:

| build | gzipped |
|---|---|
| React 19 + react-dom, rendering `<div>hi</div>` | **60.6 KB** |
| the same plus `@tanstack/charts` line chart | **87.8 KB** |
| **marginal cost of the chart layer** | **≈27 KB** |

For comparison of *order of magnitude* only — not measured here, so do not
quote these as this project's numbers: Recharts and ECharts are both
substantially heavier, Chart.js is in the same neighbourhood. 27 KB gzipped
for a grammar-of-graphics engine is light, and the 113 granular exports plus
`sideEffects: false` are why: you pay for the marks you import.

## The finding that changes the architecture

**It renders to SVG in plain Node, with no DOM.**

```
typeof document: undefined | typeof window: undefined
mark children: 3 | kind: group
svg bytes: 39528 | gz: 3355
has path data: true       points plotted: 195
```

`createChartScene()` compiles a renderer-neutral scene and
`renderChartSvg(scene, opts)` is a pure `string`-returning function. So the
chart does **not** have to cost 88 KB of JavaScript:

- **pre-render the SVG at build time** — ~3.4 KB gzipped, instant, crawlable,
  works with JavaScript disabled, and it keeps the detail pages at the zero-JS
  weight they were built for (roadmap 15);
- **load the interactive chart only when someone reaches for it** — picking
  geographies, changing the window, comparing. That is when 88 KB is worth
  spending, and not before.

Two details that make the static half work properly:

- **CSS custom properties survive into the output.** A colour range of
  `["var(--chart-1)", …]` is emitted verbatim, and axes already use
  `currentColor`. One pre-rendered SVG therefore serves light and dark themes;
  no second generation, no colour baked into the file.
- **`ariaLabel` is a required prop**, the root carries `role="img"` and
  `aria-roledescription="chart"`, and the React adapter exposes `tabIndex`,
  `onFocusChange` and `onFocusGroupChange`. Accessible-by-construction rather
  than accessible-if-you-remember.

## The risk, stated plainly

**0.14.0, six releases in six days.** This is pre-1.0 software moving fast. A
breaking change between now and when item 14 lands is likely, not unlikely.
That is survivable *because of how it is used*: the static SVG path is two
function calls behind one build script, and the interactive path is one
component on one page. If the API turns, the blast radius is a build script,
not the site.

What would change this recommendation: the project going quiet, or `defineChart`
churning across 0.x releases. Re-check the release timeline before adopting.

## One thing that cost time, worth not repeating

`lineY` takes **the data as its first argument** and channels as the second —
Observable Plot's convention, not the "options object with a data key" shape.
Called the other way it silently produces a chart with axes, ticks and an
**empty marks group**: valid SVG, no lines, no error. Two probes were spent on
that, and both looked like a rendering bug rather than a call-signature
mistake.

## Reproduce

```bash
mkdir /tmp/chartsize && cd /tmp/chartsize
npm init -y && npm i vite@^7.1.11 @vitejs/plugin-react@^5.1.0 \
  react@^19.2.0 react-dom@^19.2.0 @tanstack/charts
cp <repo>/data/spikes/charts-tanstack-probe.mjs .
node charts-tanstack-probe.mjs
```

Deliberately **not** added to `site/package.json` yet: there are no values to
chart until item 14 archives them, and a dependency that nothing renders is a
dependency nobody is maintaining.
