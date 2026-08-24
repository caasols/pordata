# Spike A4 - where the period lives on municipios pages

Roadmap 19, following A3: years were inside a `<table>` on every portugal and europa page and on neither municipios page, though both carried years elsewhere. This names the container.

Structure and counts only - no cell values (decision 1). Raw HTML is a workflow artifact, never committed.

## Verdict

- **Years in page content sit inside: `<option>` (53), `<div>` (18), `<a>` (3).**
- **53 `<option>` elements carry a year** — the period is very likely a year picker, so first/last come from the option list, not from a table. That is a different extractor from portugal/europa.
- Years also appear in attributes: <a href=>, <a onclick=>, <a title=>, <html xmlns=>, <option value=> — check these before parsing visible text.
- Average 19 `<option>` elements per page. If the geography set were inline there would be ~308; there is not, so granularity still needs its own answer.

## Per page

### municipios/522

- status 200, 358,750 bytes
- `<select>`: 2, `<option>`: 19 of which 17 contain a year
- years by enclosing element: `option` 17, `div` 6
- years in attributes: `<option value=>` 17, `<a href=>` 3, `<html xmlns=>` 1, `<a title=>` 1, `<a onclick=>` 1

### municipios/498

- status 200, 288,819 bytes
- `<select>`: 2, `<option>`: 19 of which 18 contain a year
- years by enclosing element: `option` 18, `div` 6, `a` 3
- years in attributes: `<option value=>` 18, `<a href=>` 3, `<html xmlns=>` 1, `<a title=>` 1, `<a onclick=>` 1

### municipios/230

- status 200, 251,212 bytes
- `<select>`: 2, `<option>`: 19 of which 18 contain a year
- years by enclosing element: `option` 18, `div` 6
- years in attributes: `<option value=>` 18, `<a href=>` 3, `<html xmlns=>` 1, `<a title=>` 1, `<a onclick=>` 1

