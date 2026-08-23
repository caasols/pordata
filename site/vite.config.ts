import path from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// Builds straight into ../docs (GitHub Pages root). emptyOutDir stays
// false because docs/data/ belongs to the harvest pipeline, not the UI
// build; the npm build script removes ../docs/assets before each build
// so stale hashed bundles do not accumulate.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  build: { outDir: "../docs", emptyOutDir: false },
});
