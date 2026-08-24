import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpDown, Check, ChevronDown, ChevronRight, Moon,
  Sun } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  ALL_LANGS, AREA_LABELS, AVAILABLE, initialLang, translate,
} from "@/lib/i18n";
import {
  prepare, searchAndSort,
  type Hit, type PreparedRow, type Row, type SortMode,
} from "@/lib/search";
import { cardParts, detailHref, monthYear, shortSources } from "@/lib/card";
import { formatUnit } from "@/lib/units";
import { cn } from "@/lib/utils";

// Render chunk sized to the device: roughly two viewports of cards
// (~150px each) per append, so a phone paints ~12 while a desktop
// paints ~16-30; the 800px sentinel margin hides the seams.
const CHUNK = Math.min(60,
  Math.max(10, Math.ceil(window.innerHeight / 150) * 2));

// Newest-first is the default; the pill highlights when deviating.
// (No "relevance" option until roadmap 9 lands a real blended ranking.)
const SORT_KEYS: Record<SortMode, string> = {
  new: "sortNew", old: "sortOld", az: "sortAz", za: "sortZa",
};
const DEFAULT_SORT: SortMode = "new";

function chipClass(on: boolean): string {
  return cn(
    "flex-none cursor-pointer select-none whitespace-nowrap rounded-full border px-3 py-1 text-sm font-medium outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30",
    on
      ? "border-primary bg-primary text-primary-foreground"
      : "border-border bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground",
  );
}

export function displayNames(r: PreparedRow, lang: string): [string, string] {
  const primary = lang === "pt" ? (r.name || r.name_en)
                                : (r.name_en || r.name);
  const alt = primary === r.name ? r.name_en
            : (r.name && r.name !== primary ? r.name : "");
  return [primary, alt === primary ? "" : alt];
}

function Meta({ label, value, empty }:
    { label: string; value: string; empty: string }) {
  return (
    <div className="min-w-0">
      <span className="block text-[9.5px] uppercase tracking-[0.1em]
        text-muted-foreground/75">{label}</span>
      <span
        className={cn("block line-clamp-2 text-xs tabular-nums",
          !value && "text-muted-foreground/50")}
        title={value || undefined}
      >
        {value || empty}
      </span>
    </div>
  );
}

// Reserved, deliberately inert. There are no values to plot until the
// crosswalk lands (roadmap 14), and PORDATA's own numbers are never
// redistributed, so this stays an empty slot rather than a fake curve.
function ChartSlot({ label }: { label: string }) {
  return (
    <div aria-hidden="true"
      className="mt-0.5 flex h-8 items-end rounded-sm border border-dashed
        border-border/70 bg-muted/30 px-2 pb-1">
      <span className="text-[9.5px] uppercase tracking-[0.08em]
        text-muted-foreground/60">{label}</span>
    </div>
  );
}

interface Stats { built_at: string; complete: boolean }

export default function App() {
  const [lang, setLang] = useState(initialLang);
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark"));
  const [rows, setRows] = useState<PreparedRow[] | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [active, setActive] = useState<ReadonlySet<string>>(new Set());
  const [summaryOnly, setSummaryOnly] = useState(false);
  const [sortMode, setSortMode] = useState<SortMode>(DEFAULT_SORT);

  const t = (key: string, params?: Record<string, string>) =>
    translate(lang, key, params);

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  // theme: .dark on <html>; system by default, the toggle persists
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      let stored: string | null = null;
      try { stored = localStorage.getItem("theme"); } catch { /* ok */ }
      if (stored !== "dark" && stored !== "light") setDark(e.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    Promise.all([
      fetch("data/catalogue.json").then((r) => r.json() as Promise<Row[]>),
      fetch("data/stats.json").then((r) => r.json() as Promise<Stats>)
        .catch(() => null),
    ]).then(([data, s]) => { setRows(prepare(data)); setStats(s); })
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 120);
    return () => clearTimeout(timer);
  }, [query]);

  const hits: Hit[] = useMemo(() => {
    if (!rows) return [];
    return searchAndSort(rows, debounced, active, sortMode,
      (r) => displayNames(r, lang)[0], lang, summaryOnly);
  }, [rows, debounced, active, sortMode, lang, summaryOnly]);

  // Infinite scroll: a sentinel below the list grows `shown` as it
  // nears the viewport; recreating the observer on each append makes it
  // re-evaluate the sentinel's new position.
  const [shown, setShown] = useState(CHUNK);
  useEffect(() => { setShown(CHUNK); }, [hits]);
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || shown >= hits.length) return;
    const obs = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting))
        setShown((s) => Math.min(hits.length, s + CHUNK));
    }, { rootMargin: "800px" });
    obs.observe(el);
    return () => obs.disconnect();
  }, [hits, shown]);

  const setLanguage = (l: string) => {
    setLang(l);
    try { localStorage.setItem("lang", l); } catch { /* ok */ }
  };
  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    try { localStorage.setItem("theme", next ? "dark" : "light"); }
    catch { /* ok */ }
  };
  const toggleArea = (key: string) => {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const meta = rows === null ? "" :
    (hits.length === 1 ? t("resultsOne")
      : t("results", { n: hits.length.toLocaleString(lang) })) +
    (shown < hits.length
      ? t("showing", { m: shown.toLocaleString(lang) }) : "");

  return (
    <main className="mx-auto max-w-3xl px-4 pb-16 pt-7">
      <div className="mb-1.5 flex flex-nowrap items-center justify-between gap-2.5">
        <h1 className="min-w-0 text-2xl font-bold tracking-tight">
          <a href="./" className="no-underline">pordata map</a>
        </h1>
        <div className="flex flex-shrink-0 items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button aria-label={t("langLabel")}>
                {lang.toUpperCase()}
                <ChevronDown className="size-3.5 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="max-h-[60vh]">
              {ALL_LANGS.map(([l, name]) => (
                <DropdownMenuItem
                  key={l}
                  disabled={!AVAILABLE.has(l)}
                  title={name}
                  aria-label={name}
                  onSelect={() => setLanguage(l)}
                >
                  <span>{l.toUpperCase()}</span>
                  {l === lang && <Check className="size-3.5" />}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button size="icon" aria-label={t("themeLabel")}
                  className="text-muted-foreground" onClick={toggleTheme}>
            {dark ? <Sun className="size-4" />
                  : <Moon className="size-4" />}
          </Button>
        </div>
      </div>

      {rows !== null && (
        <p
          className="mb-5 mt-2 text-sm text-muted-foreground [&_a]:text-foreground [&_a]:underline-offset-[3px] [&_b]:font-semibold [&_b]:text-foreground"
          dangerouslySetInnerHTML={{
            __html: t("intro", { n: rows.length.toLocaleString(lang) }),
          }}
        />
      )}

      <search>
        <Input
          type="search"
          autoComplete="off"
          autoFocus
          className="h-11"
          aria-label={t("searchLabel")}
          placeholder={t("placeholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </search>

      <div className="no-scrollbar mb-1.5 mt-3.5 flex flex-nowrap gap-2 overflow-x-auto pb-0.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              aria-label={`${t("sortLabel")}: ${t(SORT_KEYS[sortMode])}`}
              className={cn(chipClass(sortMode !== DEFAULT_SORT),
                "inline-flex items-center gap-1.5")}>
              <ArrowUpDown className="size-3.5" />
              {t(SORT_KEYS[sortMode])}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-[10rem]">
            {(Object.keys(SORT_KEYS) as SortMode[]).map((mode) => (
              <DropdownMenuItem
                key={mode}
                onSelect={() => setSortMode(mode)}
              >
                {t(SORT_KEYS[mode])}
                {mode === sortMode && <Check className="size-3.5" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {Object.keys(AREA_LABELS).map((key) => (
          <button
            key={key}
            aria-pressed={active.has(key)}
            className={chipClass(active.has(key))}
            onClick={() => toggleArea(key)}
          >
            {AREA_LABELS[key][lang] || key}
          </button>
        ))}
        {/* a different axis from the areas: PORDATA's own per-location
            summary set, ANDed with whatever areas are picked */}
        <button
          aria-pressed={summaryOnly}
          title={t("summaryTip")}
          className={chipClass(summaryOnly)}
          onClick={() => setSummaryOnly((v) => !v)}
        >
          {t("summaryFilter")}
        </button>
      </div>

      <div className="mx-0.5 my-3 text-sm text-muted-foreground"
           role="status" aria-live="polite">
        {meta}
      </div>

      <div>
        {failed && <div>{t("loadfail")}</div>}
        {!failed && rows !== null && hits.length === 0 && (
          <Card className="my-2.5 px-4 py-6 text-center">
            <p className="text-sm text-muted-foreground">{t("empty")}</p>
            {(query || active.size > 0 || summaryOnly) && (
              <Button
                className="mt-3"
                onClick={() => {
                  setQuery(""); setActive(new Set()); setSummaryOnly(false);
                }}
              >
                {t("clearFilters")}
              </Button>
            )}
          </Card>
        )}
        {hits.slice(0, shown).map(([, r]) => {
          const { title, coverage } = cardParts(r, lang);
          const sources = shortSources(r.fontes);
          return (
            <Card key={r.url} className="my-2.5 [overflow-wrap:anywhere]">
              {/* the whole card is the tap target, and since roadmap 15
                  it opens this project's own page rather than bouncing
                  to pordata.pt — the click-out lives there, beside the
                  chart slot it will eventually replace */}
              <a
                href={detailHref(r)}
                title={t("openDetail")}
                className="flex items-center gap-2.5 rounded-lg px-4 py-3.5
                  no-underline focus-visible:outline-none focus-visible:ring-2
                  focus-visible:ring-ring"
              >
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <h3 className="m-0 text-[15px] font-semibold leading-snug">
                    {title || r.url}
                  </h3>
                  {coverage && (
                    <p className="-mt-1.5 m-0 text-[12.5px] leading-tight
                      text-muted-foreground">{coverage}</p>
                  )}
                  <div className="flex flex-wrap gap-1.5">
                    <Badge>
                      {(AREA_LABELS[r.area] || {})[lang] || r.area}
                    </Badge>
                    {r.removed && (
                      <Badge variant="destructive">{t("removed")}</Badge>
                    )}
                    {r.featured?.length ? (
                      <Badge title={t("summaryTip")}>
                        {t("summaryFilter")}
                      </Badge>
                    ) : null}
                  </div>
                  <div className="grid grid-cols-3 gap-x-3">
                    <Meta label={t("updated")} empty={t("notAvailable")}
                      value={monthYear(r.ultima_atualizacao, lang)} />
                    <Meta label={t("unit")} empty={t("notAvailable")}
                      value={formatUnit(r.unit || "", lang)} />
                    <Meta label={t("sources")} empty={t("notAvailable")}
                      value={sources} />
                  </div>
                  <ChartSlot label={t("chartSoon")} />
                </div>
                <ChevronRight
                  aria-hidden="true"
                  className="size-4 shrink-0 text-muted-foreground/50"
                />
              </a>
            </Card>
          );
        })}
      </div>
      <div ref={sentinelRef} />

      <footer className="mt-11 border-t border-border pt-4 text-sm text-muted-foreground [&_a]:text-foreground [&_a]:underline-offset-[3px]">
        <span dangerouslySetInnerHTML={{ __html: t("foot") }} />
        {stats && (
          <div className="mt-1.5">
            {t("updatedAt")}{stats.built_at}
            {stats.complete ? "" : t("building")}
          </div>
        )}
        <div className="mt-2.5">
          Made with <span className="text-primary">&hearts;</span> by{" "}
          <a href="https://benevol.us" target="_blank" rel="noopener">
            Benevolus
          </a>{" "}
          studio
        </div>
      </footer>
    </main>
  );
}
