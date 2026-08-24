# Spike A6 - full page inventory

Two fields were discovered *after* the harvest that could have been captured during it (the unit caption, the period), and the owner spotted a third: the plain-language **question** under each title. Raw HTML is not stored, so each late discovery costs another full fetch.

So this does not search for questions. It inventories every text-bearing element by tag and class, so the next reader sees what is on the page rather than what someone thought to look for. Item 21 fires once "what else should we pull off these pages?" stops changing; this is how that gets answered.

Structure and metadata only. Numeric runs are redacted to `<number>` rather than recorded (decision 1); raw HTML is a workflow artifact, never committed.

## europa/1415

*Abastecimento público de água*

- status 200, 169,130 bytes, 34 distinct tag/class groups

### Questions found on the page

- `h2` — Que países fornecem mais e menos água canalizada?

### One-of-a-kind blocks (candidate fields)

- `div.DataSourceLegend` — Fontes/Entidades: Eurostat | OCDE | Institutos Nacionais de Estatística, PORDATA
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — Abastecimento público de água
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — EUROPA
- `span.SymbolCaption` — s

### Most repeated blocks (page furniture)

- `option` ×31 — 2019
- `span` ×21 — Metainformação
- `a` ×18 — Sobre estes dados
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Que países fornecem mais e menos água canalizada?
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## municipios/522

*Abono de família para crianças e jovens da Segurança Social*

- status 200, 358,750 bytes, 30 distinct tag/class groups

### Questions found on the page

- `h2` — Onde há mais e menos famílias, crianças e jovens a receber o apoio da Segurança Social para sustento e educação dos filhos?

### One-of-a-kind blocks (candidate fields)

- `h1` — Abono de família para crianças e jovens da Segurança Social
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `td` — (A) Requerente (B) Titular
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS

### Most repeated blocks (page furniture)

- `a` ×23 — Sobre estes dados
- `option` ×19 — 2025
- `span` ×17 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde há mais e menos famílias, crianças e jovens a receber o apoio da Segurança 
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## portugal/1088

*Abastecimento de água: água captada, água tratada e água distribuída/consumida (1991-2006)*

- status 200, 174,916 bytes, 36 distinct tag/class groups

### Questions found on the page

- `h2` — Quanta água é captada, tratada e distribuída pela rede pública?

### One-of-a-kind blocks (candidate fields)

- `h1` — Abastecimento de água: água captada, água tratada e água distribuída/consumida (1991-2006)
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.NonTotalContainer2` — Água captada para abastecimento
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `span.Bold` — Indicador
- `div.MobileTitle_Wrapper` — PORTUGAL
- `div.YearCurrentText` — 2006
- `div.YearOtherText` — 1991

### Most repeated blocks (page furniture)

- `td.ValueCell` ×42 — <number>
- `span` ×21 — Metainformação
- `a` ×20 — Sobre estes dados
- `td.YearCell` ×16 — 1991
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `span.SymbolCaption` ×10 — ┴
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Quanta água é captada, tratada e distribuída pela rede pública?

