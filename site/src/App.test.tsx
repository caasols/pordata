import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Row } from "./lib/search";

const ROWS: Row[] = [
  { id: 1, area: "portugal", name: "Taxa de natalidade",
    name_en: "Birth rate", description: "Nados-vivos por mil habitantes",
    fontes: ["INE", "PORDATA"], ultima_atualizacao: "2026-01-01",
    url: "https://www.pordata.pt/portugal/taxa+de+natalidade-1",
    harvested_at: "2026-08-22" },
  { id: 2, area: "europa", name: "Índice de Gini",
    name_en: "Gini index", description: "Desigualdade de rendimento",
    fontes: ["Eurostat"], ultima_atualizacao: "2025-05-05",
    url: "https://www.pordata.pt/europa/indice+de+gini-2",
    harvested_at: "2026-08-22" },
  { id: 3, area: "municipios", name: "Médicos", name_en: "Doctors",
    description: "Por mil habitantes", fontes: ["INE, PORDATA"],
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

// jsdom's navigator.language is en-US, so the UI comes up in English
describe("App", () => {
  it("renders fetched indicators newest-first with count", async () => {
    render(<App />);
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
    expect(screen.getByText("3 indicators")).toBeInTheDocument();
    const links = screen.getAllByRole("link")
      .map((a) => a.textContent)
      .filter((s) => ["Birth rate", "Gini index", "Doctors"].includes(s!));
    expect(links).toEqual(["Birth rate", "Gini index", "Doctors"]);
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
    expect(screen.getByText("1 indicators")).toBeInTheDocument();
  });

  it("area chips filter opt-in and toggle off", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Europe" }));
    await waitFor(() =>
      expect(screen.queryByText("Birth rate")).not.toBeInTheDocument());
    expect(screen.getByText("Gini index")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Europe" }));
    expect(await screen.findByText("Birth rate")).toBeInTheDocument();
  });

  it("sort menu switches to A-Z", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: /Newest first/ }));
    await user.click(await screen.findByRole("menuitem", { name: "Name A→Z" }));
    await waitFor(() => {
      const links = screen.getAllByRole("link")
        .map((a) => a.textContent)
        .filter((s) => ["Birth rate", "Gini index", "Doctors"].includes(s!));
      expect(links).toEqual(["Birth rate", "Doctors", "Gini index"]);
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

  it("switching to PT localizes UI and shows descriptions", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Birth rate");
    await user.click(screen.getByRole("button", { name: "Language" }));
    await user.click(await screen.findByRole("menuitem", { name: "Português" }));
    expect(await screen.findByText("3 indicadores")).toBeInTheDocument();
    expect(screen.getByText("Taxa de natalidade")).toBeInTheDocument();
    expect(screen.getByText("Nados-vivos por mil habitantes"))
      .toBeInTheDocument();
    expect(localStorage.getItem("lang")).toBe("pt");
  });

  it("footer carries the studio credit and build state", async () => {
    render(<App />);
    await screen.findByText("Birth rate");
    expect(screen.getByText("Benevolus")).toBeInTheDocument();
    expect(screen.getByText(/2026-08-23 09:00 UTC/)).toBeInTheDocument();
  });
});
