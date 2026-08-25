import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

// Everything under src/lib is inside StrykerJS's `mutate` glob and
// vitest's coverage include, so an unwired module sits inside two
// quality gates while reaching no user. `recency.ts` did exactly that —
// its own tests kept it green and tree-shaking kept it out of the
// bundle, while context.md described it as shipped.
//
// Not a dependency-graph tool: a list that has to be edited when a
// module stops being wired is the point, because that edit is where
// someone states the intent.
const NOT_IMPORTED_BY_THE_APP: Record<string, string> = {
  "recency.ts":
    "roadmap 8c — the freshness label is built and has no consumer yet",
  "contrast.ts":
    "a checking tool, not app code: it lives here on purpose because "
    + "src/lib is what StrykerJS mutates",
};

const ROOT = resolve(process.cwd(), "src");

function sources(): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const full = resolve(dir, e.name);
      if (e.isDirectory()) walk(full);
      else if (/\.tsx?$/.test(e.name) && !/\.test\.tsx?$/.test(e.name))
        out.push(full);
    }
  };
  walk(ROOT);
  return out;
}

describe("every lib module reaches the app", () => {
  const files = sources();
  const libs = readdirSync(resolve(ROOT, "lib"))
    .filter((f) => /\.tsx?$/.test(f) && !/\.test\.tsx?$/.test(f)
                   && !/\.d\.ts$/.test(f));

  it.each(libs)("%s is imported, or declared with a reason", (lib) => {
    const stem = lib.replace(/\.tsx?$/, "");
    const importers = files.filter(
      (f) => !f.endsWith(`/lib/${lib}`)
        && new RegExp(`from ["'](@/lib/|\\./|\\.\\./lib/)${stem}["']`)
          .test(readFileSync(f, "utf8")));
    if (importers.length) return;
    expect(
      NOT_IMPORTED_BY_THE_APP[lib],
      `src/lib/${lib} is imported by nothing and is not in NOT_IMPORTED_BY_THE_APP`,
    ).toBeTruthy();
  });

  it("does not excuse a module that no longer exists", () => {
    for (const name of Object.keys(NOT_IMPORTED_BY_THE_APP)) {
      expect(libs, `${name} is in NOT_IMPORTED_BY_THE_APP but not on disk`)
        .toContain(name);
    }
  });
});
