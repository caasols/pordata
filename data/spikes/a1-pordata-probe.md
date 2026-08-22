# Spike A1: PORDATA indicator page probe

Question: is catalogue metadata in the server-rendered HTML, or client-side? Raw HTML in the workflow artifact `spike-raw`.

## `portugal/abastecimento+de+agua+agua+captada++agua+tratada+e+agua+distribuida+consumida+(1991+2006)-1088`

- HTTP 200, 174,915 bytes, text/html; charset=utf-8
- `<title>`: 'Portugal: Abastecimento de água: água captada, água tratada e água distribuída/consumida (1991-2006) | Pordata'
- `<script>` tags: 72, JSON-LD blocks: 1
- Marker counts: `Fontes`=9, `Entidades`=9, `atualiza`=1, `actualiza`=3, `OSFillParent`=8, `screenservices`=0, `application/json`=0, `<table`=15, `og:title`=1

## `municipios/abono+de+familia+para+criancas+e+jovens+da+seguranca+social-522`

- HTTP 200, 358,702 bytes, text/html; charset=utf-8
- `<title>`: 'Municípios: Abono de família para crianças e jovens da Segurança Social | Pordata'
- `<script>` tags: 76, JSON-LD blocks: 1
- Marker counts: `Fontes`=11, `Entidades`=11, `atualiza`=2, `actualiza`=3, `OSFillParent`=8, `screenservices`=0, `application/json`=0, `<table`=12, `og:title`=1

## `europa/abastecimento+publico+de+agua-1415`

- HTTP 200, 169,130 bytes, text/html; charset=utf-8
- `<title>`: 'Europa: Abastecimento público de água | Pordata'
- `<script>` tags: 76, JSON-LD blocks: 1
- Marker counts: `Fontes`=10, `Entidades`=10, `atualiza`=1, `actualiza`=3, `OSFillParent`=8, `screenservices`=0, `application/json`=0, `<table`=16, `og:title`=1

## Verdict (heuristic)

Fontes/Entidades present in server HTML on every sampled page: **True**. A plain-HTTP harvester should work.
