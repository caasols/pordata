# Catalogue QA

Records: 2196 (2195 ok, 0 errored)

## Field coverage (% non-empty)

| area | n | name | description | fontes | ultima_atualizacao | json_ld |
|---|---|---|---|---|---|---|
| europa | 638 | 100% | 100% | 100% | 100% | 100% |
| municipios | 504 | 100% | 100% | 100% | 100% | 100% |
| portugal | 1053 | 100% | 100% | 100% | 100% | 100% |
| ALL | 2195 | 100% | 100% | 100% | 100% | 100% |

## Findings

- empty name: 3
  - `financiamento+da+uniao+europeia+aos+paises+em+desenvolvimento-3597`
  - `taxa+de+atividade+total+e+por+grupo+etario-3828`
  - `votos+validos+na+eleicao+para+a+assembleia+legislativa+da+regiao+auton`
- name/description carries inline HTML (stripped at build): 25
  - `administracoes+publicas+despesa+em+tribunais+per+capita-3590`
  - `apoio+do+governo+a+investigacao+e+desenvolvimento+(i+d)+na+agricultura`
  - `consumo+de+energia+final+das+familias+per+capita-3551`
  - `emissao+media+de+co2+por+km+dos+automoveis+novos+de+passageiros-3611`
  - `emissoes+de+gases+com+efeito+de+estufa+per+capita-3360`
  - `empresas+com+10+e+mais+pessoas+ao+servico+com+website+ou+homepage+em+p`
  - `empresas+com+10+e+mais+pessoas+ao+servico+com+website+ou+homepage+em+p`
  - `pegada+material+per+capita-3745`

## Abandoned (listed by PORDATA, not served)

Skipped by the harvest plan and tombstoned at build time; see `data/catalogue/abandoned.txt`.

- `portugal/despesas+das+administracoes+publicas+em+ambiente+em+percentagem+do+tota`: HTTP Error 500: Internal Server Error

## Published layer (docs/data/catalogue.json)

- rows: 2195 (2195 live, 0 tombstoned)
- name_en present: 100%
- fontes non-empty: 100%
- featured flagged rows: 43
- breakdown line: 54%
- unit: 52%
- either (coverage line renders): 78%

## Payload budget (roadmap 6f)

Gzipped KB a first visit downloads before it can search: the page, its bundle and the whole catalogue. Levers, measured, for when a ceiling breaks: `url` is ~25% of the gzipped catalogue and derivable from area+slug; `description` is ~12% for a field the UI never renders.

- first load: **264.9 KB** (ceiling 400)
- of which catalogue.json: **151.7 KB** (ceiling 250)

## Gate

Thresholds are machine-checked (decision 7b); `--strict` exits non-zero on breach so a bad harvest never publishes.

- jsonl_skipped_lines: 0
- ok_records_ratio: 0.9995
- name_coverage: 0.9986
- description_coverage: 0.9986
- fontes_coverage: 1
- date_iso_ratio: 1
- duplicate_area_id: 0
- parse_warnings: 0
- published_rows_ratio: 1
- breakdown_ratio: 0.5449
- unit_ratio: 0.5185
- revision_ratio: 0.09248
- question_ratio: 0
- period_ratio: 0
- breakdown_ratio_by_area: europa 49%, municipios 60%, portugal 55%
- unit_ratio_by_area: europa 100%, municipios 100%, portugal 0%
- question_ratio_by_area: europa 0%, municipios 0%, portugal 0%
- period_ratio_by_area: europa 0%, municipios 0%, portugal 0%
- separator_repairs: 37
- unit_contamination: 0
- unit_translated_ratio: 1
- featured_collisions: 0
- featured_rows: 43
- orgs_coverage: 0.9941
- distinct_orgs: 127
- first_load_gzip_kb: 264.9
- catalogue_gzip_kb: 151.7

- all thresholds pass
