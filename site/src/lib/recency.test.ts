import { describe, expect, it } from "vitest";

import { recency, STALE_YEARS } from "./recency";

const NOW = new Date("2026-08-25T00:00:00Z");

describe("recency", () => {
  it("counts the current calendar year as current", () => {
    expect(recency("2026-01-02", NOW)).toBe("current");
    expect(recency("2026-12-31", NOW)).toBe("current");
  });

  it("treats a future date as current rather than as an error", () => {
    // PORDATA stamps some rows ahead of the day they are published; a
    // future date is odd but it is certainly not stale
    expect(recency("2027-03-01", NOW)).toBe("current");
  });

  it("keeps everything inside the window as recent", () => {
    expect(recency("2025-06-01", NOW)).toBe("recent");
    expect(recency(`${2026 - STALE_YEARS}-01-01`, NOW)).toBe("recent");
  });

  it("turns stale exactly one year past the window", () => {
    // the boundary is the whole point of the bucket, so it is pinned
    // from both sides rather than sampled in the middle
    expect(recency(`${2026 - STALE_YEARS}-12-31`, NOW)).toBe("recent");
    expect(recency(`${2026 - STALE_YEARS - 1}-12-31`, NOW)).toBe("stale");
  });

  it("reports a missing date as unknown, not as stale", () => {
    // a third state on purpose: a parse regression upstream would
    // otherwise make every row look ancient instead of unreadable
    expect(recency("", NOW)).toBe("");
    expect(recency(undefined, NOW)).toBe("");
  });

  it("reports an unparseable date as unknown", () => {
    expect(recency("2026", NOW)).toBe("");
    expect(recency("25/08/2026", NOW)).toBe("");
    expect(recency("not a date", NOW)).toBe("");
  });

  it("reads the year in UTC so the bucket does not depend on the viewer", () => {
    // 31 December 23:00 UTC is already 1 January in Lisbon in winter;
    // using the local year would put two viewers in different buckets
    expect(recency("2026-05-01", new Date("2026-12-31T23:00:00Z"))).toBe("current");
  });

  it("moves a row from current to recent when the year turns", () => {
    // the reason this is derived rather than stored: a bucket baked in
    // at build time is wrong the moment the calendar advances, and the
    // harvest only rebuilds rows whose records changed
    expect(recency("2026-06-01", NOW)).toBe("current");
    expect(recency("2026-06-01", new Date("2027-01-01T00:00:00Z"))).toBe("recent");
  });
});
