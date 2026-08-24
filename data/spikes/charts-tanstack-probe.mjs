import { defineChart, createChartScene } from "@tanstack/charts/scene";
import { renderChartSvg } from "@tanstack/charts/svg";
import { lineY } from "@tanstack/charts/line";
import { scaleLinear } from "@tanstack/charts/scales/linear";
import { scaleOrdinal } from "@tanstack/charts/scales/ordinal";
import { gzipSync } from "node:zlib";

const data = [];
for (const geo of ["PT", "ES", "FR"])
  for (let y = 1960; y <= 2024; y++)
    data.push({ ano: y, valor: 60 + Math.sin((y + geo.length) / 4) * 25, geo });

const chart = defineChart({
  x: { scale: scaleLinear().domain([1960, 2024]).nice() },
  y: { scale: scaleLinear().domain([0, 100]).nice() },
  color: { scale: scaleOrdinal().domain(["PT", "ES", "FR"])
                                .range(["#b45309", "#0e7490", "#4d7c0f"]) },
  marks: [lineY(data, { x: (d) => d.ano, y: (d) => d.valor,
                        z: (d) => d.geo, color: (d) => d.geo, strokeWidth: 2 })],
});
const scene = createChartScene(chart, { width: 640, height: 320 });
const marks = scene.nodes.find((n) => n.key === "marks");
console.log("mark children:", marks.children.length, "| kind:", marks.children[0]?.kind);
const svg = renderChartSvg(scene, { ariaLabel: "Taxa de desemprego" });
console.log("svg bytes:", svg.length, "| gz:", gzipSync(Buffer.from(svg)).length);
console.log("has path data:", /<path[^>]+d="M/.test(svg));
console.log("points plotted:", (svg.match(/[ML]\d/g) || []).length);
