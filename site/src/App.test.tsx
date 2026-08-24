import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App, { displayNames } from "./App";
import { prepare } from "./lib/search";
import type { Row } from "./lib/search";

const ROWS: Row[] = [
  { id: 1, area: "portugal",
    name: "Taxa de natalidade: total e por sexo",
    title: "Taxa de natalidade", breakdown: "total e por sexo",
    unit: "Taxa - \u2030",
    name_en: "Birth rate", description: "Nados-vivos por mil habitantes",
    fontes: ["INE", "PORDATA"], ultima_atualizacao: "2026-01-01",
    url: "https://www.pordata.pt/portugal/taxa+de+natalidade-1",
    harvested_at: "2026-08-22" },
  { id: 2, area: "europa", name: "Índice de Gini",
    name_en: "Gini index", description: "Desigualdade de rendimento",
    fontes: ["Eurostat"], ultima_atualizacao: "2025-05-05",
    featured: ["quadro_resumo"],
    url: "https://www.pordata.pt/europa/indice+de+gini-2",
    harvested_at: "2026-08-22" },
  { id: 3, area: "municipios", name: "Médicos", name_en: "Doctors",
    title: "Médicos", breakdown: "", unit: "",
    description: "Por mil habitantes",
    fontes: ["SGMAI - Base de Dados do Recenseamento", "CNE", "PORDATA"],
    ultima_atualizacao: "2024-03-03", removed: true,
    url: "https://www.pordata.pt/municipios/medicos-3",
    harvested_at: "2026-08-22" },
];

const STATS = { built_at: "2026-08-23 09:00 UTC", complete: false };

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((url: string) =>
    Promise.resolve({
      json: () => Promise.resolve(
        String(url).includes("stats") ? STATS : ROWS),
    })));
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  document.documentElement.classList.remove("dark");
});

// The whole card is one link, so the card title is queried as a heading
// rather than as link text.
const headings = () =>
  screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);

// jsdom's navigator.language is en-US, so the UI comes up in English
describe("App", () => {
  it("renders fetched indicators newest-first with count", async () => {
    render(<App />);
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
    expect(screen.getByText("3 indicators")).toBeInTheDocument();
    expect(headings()).toEqual(["Birth rate", "Gini index", "Doctors"]);
    // every card is one tap target wrapping the whole row, and since
    // roadmap 15 it opens this project's own page rather than bouncing
    // to pordata.pt — the click-out moved to the detail page, beside the
    // chart slot it will eventually replace
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("indicador/portugal/1/");
    expect(hrefs).not.toContain(
      "https://www.pordata.pt/portugal/taxa+de+natalidade-1");
    // discontinued badge on the tombstoned row
    expect(screen.getByText("discontinued")).toBeInTheDocument();
  });

  it("search narrows results after the debounce", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.type(screen.getByRole("searchbox"), "gini");
    await waitFor(() =>
      expect(screen.queryByText("Birth rate")).not.toBeInTheDocument());
    expect(screen.getByText("Gini index")).toBeInTheDocument();
    expect(screen.getByText("1 indicator")).toBeInTheDocument();
  });

  it("area chips filter opt-in and toggle off", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    const chip = screen.getByRole("button", { name: "Europe" });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    await user.click(chip);
    await waitFor(() =>
      expect(screen.queryByText("Birth rate")).not.toBeInTheDocument());
    expect(screen.getByText("Gini index")).toBeInTheDocument();
    expect(chip).toHaveAttribute("aria-pressed", "true");
    await user.click(chip);
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
  });

  it("sort menu switches to A-Z", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: /Newest first/ }));
    await user.click(await screen.findByRole("menuitem", { name: "Name A→Z" }));
    await waitFor(() => {
      expect(headings()).toEqual(["Birth rate", "Doctors", "Gini index"]);
    });
  });

  it("theme toggle flips the dark class and persists", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Light/dark theme" }));
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
  });

  it("language menu greys out unavailable languages", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Language" }));
    const items = await screen.findAllByRole("menuitem");
    expect(items).toHaveLength(24);
    const disabled = items.filter((i) => i.hasAttribute("data-disabled"));
    expect(disabled).toHaveLength(22);
  });

  it("switching to PT localizes UI and splits title from breakdown", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Language" }));
    await user.click(await screen.findByRole("menuitem", { name: "Português" }));
    expect(await screen.findByText("3 indicadores")).toBeInTheDocument();
    // the PT card shows the split title, never the full colon string
    expect(headings()).toContain("Taxa de natalidade");
    expect(headings()).not.toContain("Taxa de natalidade: total e por sexo");
    expect(screen.getByText("total e por sexo")).toBeInTheDocument();
    // PORDATA's description is boilerplate on 96.3% of rows - it is gone
    expect(screen.queryByText("Nados-vivos por mil habitantes"))
      .not.toBeInTheDocument();
    expect(localStorage.getItem("lang")).toBe("pt");
  });

  it("shows the coverage line, unit and month-precision freshness", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Language" }));
    await user.click(await screen.findByRole("menuitem", { name: "Português" }));
    await screen.findByText("3 indicadores");
    // PT keeps the Portuguese unit
    expect(screen.getByText("Taxa - \u2030")).toBeInTheDocument();
    // 2026-01-01 rendered as a month, not an ISO date
    expect(screen.queryByText("2026-01-01")).not.toBeInTheDocument();
    // long source lists collapse to the first entity plus a count
    expect(screen.getByText("SGMAI +2")).toBeInTheDocument();
  });

  it("the breakdown line rides with the PT name only", async () => {
    render(<App />);
    // English UI: the EN name has no colon structure to split
    await screen.findByText("Birth rate");
    expect(screen.queryByText("total e por sexo")).not.toBeInTheDocument();
  });

  it("shows no intro count while the catalogue is loading", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(<App />);
    expect(document.querySelector("main p")).toBeNull();
  });

  it("controls expose accessible names, not just placeholders", async () => {
    render(<App />);
    await screen.findByText("Birth rate");
    expect(screen.getByRole("searchbox", { name: "Search indicators" }))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Language" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Light/dark theme" }))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Sort: / })).toBeInTheDocument();
  });

  it("announces the result count to assistive tech", async () => {
    render(<App />);
    await screen.findByText("Birth rate");
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("3 indicators");
    expect(status).toHaveAttribute("aria-live", "polite");
  });

  it("empty results show a message and a working clear-filters action",
     async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.type(screen.getByRole("searchbox"), "zzzzzznothing");
    expect(await screen.findByText("No indicators match this search."))
      .toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
    expect(screen.queryByText("No indicators match this search."))
      .not.toBeInTheDocument();
  });

  it("clear-filters is offered only when something is filtering", async () => {
    render(<App />);
    await screen.findByText("Birth rate");
    expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
  });

  it("keeps the meta columns aligned whether or not there is a unit",
     async () => {
    const { container } = render(<App />);
    await screen.findByText("Birth rate");
    const grids = container.querySelectorAll("div.grid-cols-3");
    expect(grids).toHaveLength(3);          // one meta row per card
    // Every card reserves all three cells, so ATUAL./UNIDADE/FONTES start
    // at the same x down the list. Two of the three fixtures have no unit.
    grids.forEach((g) => expect(g.children).toHaveLength(3));
    // Two of the three fixtures have no unit; those cells keep their
    // label and show the placeholder rather than going blank.
    const placeheld = [...grids].filter(
      (g) => g.children[1].textContent === "unitn/a");
    expect(placeheld).toHaveLength(2);
    // the card that does have one renders it, translated: the fixture's
    // "Taxa - \u2030" is Portuguese and the UI here is English
    expect(screen.getByText("Rate - \u2030")).toBeInTheDocument();
    expect(screen.queryByText("Taxa - \u2030")).not.toBeInTheDocument();
    expect(screen.getAllByText("n/a")).toHaveLength(2);
  });

  it("badges the summary set with a plain label, not the raw value",
     async () => {
    render(<App />);
    await screen.findByText("Birth rate");
    // badge and filter pill carry the same word, so both match
    expect(screen.getAllByText("Summary").length).toBeGreaterThan(1);
    expect(screen.queryByText(/quadro_resumo/)).not.toBeInTheDocument();
    // PORDATA attribution moved to the badge's tooltip
    const badge = screen.getAllByText("Summary")
      .find((el) => el.getAttribute("title"));
    expect(badge?.getAttribute("title")).toMatch(/PORDATA/);
  });

  it("summary pill filters to PORDATA's per-location set and toggles off",
     async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    const pill = screen.getByRole("button", { name: "Summary" });
    expect(pill).toHaveAttribute("aria-pressed", "false");
    await user.click(pill);
    await waitFor(() =>
      expect(screen.queryByText("Birth rate")).not.toBeInTheDocument());
    expect(screen.getByText("Gini index")).toBeInTheDocument();
    expect(screen.getByText("1 indicator")).toBeInTheDocument();
    expect(pill).toHaveAttribute("aria-pressed", "true");
    await user.click(pill);
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
  });

  it("summary ANDs with the area pills rather than replacing them",
     async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Summary" }));
    await user.click(screen.getByRole("button", { name: "Portugal" }));
    // portugal has no summary rows in the fixture -> empty, not "all"
    expect(await screen.findByText("No indicators match this search."))
      .toBeInTheDocument();
  });

  it("clear-filters also releases the summary pill", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Summary" }));
    await user.click(screen.getByRole("button", { name: "Portugal" }));
    await user.click(await screen.findByRole("button", { name: "Clear filters" }));
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Summary" }))
      .toHaveAttribute("aria-pressed", "false");
  });

  it("footer carries the studio credit and build state", async () => {
    render(<App />);
    await screen.findByText("Birth rate");
    expect(screen.getByText("Benevolus")).toBeInTheDocument();
    expect(screen.getByText(/2026-08-23 09:00 UTC/)).toBeInTheDocument();
  });
});

describe("displayNames", () => {
  const mk = (name: string, name_en: string) =>
    prepare([{ id: 9, area: "portugal", name, name_en, description: "",
      fontes: [], ultima_atualizacao: "", url: "u",
      harvested_at: "" }])[0];

  it("PT shows PT first with EN below; EN the reverse", () => {
    expect(displayNames(mk("Taxa", "Rate"), "pt")).toEqual(["Taxa", "Rate"]);
    expect(displayNames(mk("Taxa", "Rate"), "en")).toEqual(["Rate", "Taxa"]);
  });
  it("falls back across languages when one name is missing", () => {
    expect(displayNames(mk("", "Rate"), "pt")).toEqual(["Rate", ""]);
    expect(displayNames(mk("Taxa", ""), "en")).toEqual(["Taxa", ""]);
  });
  it("never repeats an identical name as the alt line", () => {
    expect(displayNames(mk("Portugal 2030", "Portugal 2030"), "pt"))
      .toEqual(["Portugal 2030", ""]);
    expect(displayNames(mk("Portugal 2030", "Portugal 2030"), "en"))
      .toEqual(["Portugal 2030", ""]);
  });
});

