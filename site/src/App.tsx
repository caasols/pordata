import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpDown, Check, ChevronDown, Moon, Sun } from "lucide-react";

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
import { cn } from "@/lib/utils";

// Render chunk sized to the device: roughly two viewports of cards
// (~150px each) per append, so a phone paints ~12 while a desktop
// paints ~16-30; the 800px sentinel margin hides the seams.
const CHUNK = Math.min(60,
  Math.max(10, Math.ceil(window.innerHeight / 150) * 2));

const SORT_KEYS: Record<SortMode, string> = {
  relevance: "sortRelevance", az: "sortAz", za: "sortZa",
  new: "sortNew", old: "sortOld",
};

function chipClass(on: boolean): string {
  return cn(
    "flex-none cursor-pointer select-none whitespace-nowrap rounded-full border px-3 py-1 text-[.82rem] font-medium",
    on
      ? "border-primary bg-primary text-primary-foreground"
      : "border-border bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground",
  );
}

function displayNames(r: PreparedRow, lang: string): [string, string] {
  const primary = lang === "pt" ? (r.name || r.name_en)
                                : (r.name_en || r.name);
  const alt = primary === r.name ? r.name_en
            : (r.name && r.name !== primary ? r.name : "");
  return [primary, alt];
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
  const [sortMode, setSortMode] = useState<SortMode>("relevance");

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
      (r) => displayNames(r, lang)[0], lang);
  }, [rows, debounced, active, sortMode, lang]);

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
    t("results", { n: hits.length.toLocaleString() }) +
    (shown < hits.length ? t("showing", { m: String(shown) }) : "");

  return (
    <main className="mx-auto max-w-3xl px-4 pb-16 pt-7">
      <div className="mb-1.5 flex flex-nowrap items-center justify-between gap-2.5">
        <h1 className="min-w-0 text-[1.45rem] font-bold tracking-[-0.02em]">
          <a href="./" className="no-underline">pordata map</a>
        </h1>
        <div className="flex flex-shrink-0 items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button aria-label="Language">
                {lang.toUpperCase()}
                <ChevronDown className="size-[.85rem] text-muted-foreground" />
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
                  {l === lang && <Check className="size-[.9rem]" />}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button size="icon" aria-label="Light/dark theme"
                  className="text-muted-foreground" onClick={toggleTheme}>
            {dark ? <Sun className="size-[1.05rem]" />
                  : <Moon className="size-[1.05rem]" />}
          </Button>
        </div>
      </div>

      <p
        className="mb-5 mt-2 text-[.92rem] text-muted-foreground [&_a]:text-foreground [&_a]:underline-offset-[3px] [&_b]:font-semibold [&_b]:text-foreground"
        dangerouslySetInnerHTML={{
          __html: t("intro",
            { n: (rows?.length ?? 0).toLocaleString() }),
        }}
      />

      <Input
        type="search"
        autoComplete="off"
        autoFocus
        className="h-11"
        placeholder={t("placeholder")}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <div className="no-scrollbar mb-1.5 mt-3.5 flex flex-nowrap gap-2 overflow-x-auto pb-0.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className={cn(chipClass(sortMode !== "relevance"),
                "inline-flex items-center gap-1.5")}>
              <ArrowUpDown className="size-[.8rem]" />
              {t(SORT_KEYS[sortMode])}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-[10rem]">
            {(Object.keys(SORT_KEYS) as SortMode[]).map((mode) => (
              <DropdownMenuItem
                key={mode}
                aria-selected={mode === sortMode}
                onSelect={() => setSortMode(mode)}
              >
                {t(SORT_KEYS[mode])}
                {mode === sortMode && <Check className="size-[.9rem]" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {Object.keys(AREA_LABELS).map((key) => (
          <button
            key={key}
            className={chipClass(active.has(key))}
            onClick={() => toggleArea(key)}
          >
            {AREA_LABELS[key][lang] || key}
          </button>
        ))}
      </div>

      <div className="mx-0.5 my-3 text-[.82rem] text-muted-foreground">
        {meta}
      </div>

      <div>
        {failed && <div>{t("loadfail")}</div>}
        {hits.slice(0, shown).map(([, r]) => {
          const [primary, alt] = displayNames(r, lang);
          return (
            <Card key={r.url} className="my-2.5 px-4 py-3.5 [overflow-wrap:anywhere]">
              <a
                href={r.url}
                rel="noopener"
                className="text-[.98rem] font-semibold text-primary no-underline underline-offset-[3px] hover:underline"
              >
                {primary || r.url}
              </a>
              {alt && (
                <div className="mt-0.5 text-[.84rem] text-muted-foreground">
                  {alt}
                </div>
              )}
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge>{(AREA_LABELS[r.area] || {})[lang] || r.area}</Badge>
                {r.removed && (
                  <Badge variant="destructive">{t("removed")}</Badge>
                )}
                {(r.featured || []).map((f) => (
                  <Badge key={f}>★ {f}</Badge>
                ))}
                {r.fontes && r.fontes.length > 0 && (
                  <Badge variant="outline">
                    {t("sources")}: {r.fontes.join(", ")}
                  </Badge>
                )}
                {r.ultima_atualizacao && (
                  <Badge variant="outline">
                    {t("updated")} {r.ultima_atualizacao}
                  </Badge>
                )}
              </div>
              {lang === "pt" && r.description && (
                <p className="mt-2 text-[.88rem] text-muted-foreground">
                  {r.description}
                </p>
              )}
            </Card>
          );
        })}
      </div>
      <div ref={sentinelRef} />

      <footer className="mt-11 border-t border-border pt-4 text-[.82rem] text-muted-foreground [&_a]:text-foreground [&_a]:underline-offset-[3px]">
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
