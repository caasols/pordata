# Spike A3 - period, geography and unit in the page HTML

> **Correction, 2026-08-25.** The `A carregar conteúdo: 0` counts below are a false negative, not a result. This probe matched a literal string against entity-encoded HTML, so the marker could not have been found whether or not it was there; spike A6 later found it. CLAUDE.md names this as a standing lesson — check a "0 occurrences" result before believing it — and the killed-hypothesis reading that came from these lines is withdrawn.

Roadmap 19. Answers whether a re-harvest can recover the coverage fields the card is missing, or whether they have to come from upstream instead.

Structure and counts only - no PORDATA cell values are extracted or recorded here (decision 1). Raw HTML is a workflow artifact, never committed.

## Verdict

- **Unit, portugal: the caption IS in the HTML.** The harvester's marker windows miss it, so the fix is a new marker plus a re-harvest, not a new data source. Closes most of roadmap 20.
- Control holds: europa/municipios pages do carry the caption, as their 100% unit coverage implies.
- **Period: partial.** 5 of 7 pages have table years. Find what separates them before committing.

## Per page

### portugal/1088

- status 200, 174,915 bytes
- unit in catalogue today: (none)
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 15, '<thead': 1, '<select': 1, '<option': 3}, 15 tables, 3 options
- years anywhere: (1991, 2024, 20)
- years inside tables: (1991, 2006, 16)

### portugal/3459

- status 200, 177,258 bytes
- unit in catalogue today: (none)
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 15, '<thead': 1, '<select': 1, '<option': 3}, 15 tables, 3 options
- years anywhere: (1995, 2026, 21)
- years inside tables: (2007, 2023, 17)

### portugal/1063

- status 200, 178,193 bytes
- unit in catalogue today: (none)
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 15, '<thead': 1, '<select': 1, '<option': 2}, 15 tables, 2 options
- years anywhere: (1981, 2026, 46)
- years inside tables: (1981, 2025, 45)

### europa/1415

- status 200, 169,131 bytes
- unit in catalogue today: m 3 - Milhões
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 16, '<thead': 0, '<select': 2, '<option': 31}, 16 tables, 31 options
- years anywhere: (1989, 2026, 34)
- years inside tables: (1989, 2020, 3)

### europa/3393

- status 200, 172,260 bytes
- unit in catalogue today: Registos
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 18, '<thead': 0, '<select': 2, '<option': 23}, 18 tables, 23 options
- years anywhere: (2002, 2026, 24)
- years inside tables: (2002, 2024, 3)

### municipios/522

- status 200, 358,751 bytes
- unit in catalogue today: (A) Requerente (B) Titular
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 12, '<thead': 0, '<select': 2, '<option': 19}, 13 tables, 19 options
- years anywhere: (2009, 2026, 18)
- years inside tables: None

### municipios/498

- status 200, 288,819 bytes
- unit in catalogue today: Rácio - ‰
- caption markers: {'ver tabela completa': 1, 'gráfico ampliado': 0, 'ampliado': 1}
- client-render markers: {'A carregar conteúdo': 0, 'carregar conteúdo': 0, '/screenservices/': 0, 'OutSystems': 0, 'application/json': 0}
- structure: {'<table': 12, '<thead': 0, '<select': 2, '<option': 19}, 13 tables, 19 options
- years anywhere: (1991, 2026, 19)
- years inside tables: None

