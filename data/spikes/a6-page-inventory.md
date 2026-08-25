# Spike A6 - full page inventory

> **Correction, 2026-08-25.** The two "none matched" lines below are stale. The `<h2>` question selector was fixed in `8eaa9d2` at 13:37, seven minutes *after* this report was generated (`c8d706a`, 13:30), so the report records the pre-fix run while its own repeated-blocks lists show the questions present. The corrected figure is **15/15**, which is what CLAUDE.md and context.md cite; re-run the a6 probe to regenerate this file against the fixed parser.

Two fields were discovered *after* the harvest that could have been captured during it (the unit caption, the period), and the owner spotted a third: the plain-language **question** under each title. Raw HTML is not stored, so each late discovery costs another full fetch.

So this does not search for questions. It inventories every text-bearing element by tag and class, so the next reader sees what is on the page rather than what someone thought to look for. Item 21 fires once "what else should we pull off these pages?" stops changing; this is how that gets answered.

Structure and metadata only. Numeric runs are redacted to `<number>` rather than recorded (decision 1); raw HTML is a workflow artifact, never committed.

## portugal/67

*Greves: total e por setor de atividade económica*

- selected as: median of 911 pages with markers Entidades+Fontes+ltima actualiza
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 184,099 bytes, 35 distinct tag/class groups

### Questions found on the page

- `h2` — Quantas vezes param os empregados de trabalhar para reivindicar direitos, nos setores primário, secundário ou terciário?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — Greves: total e por setor de atividade económica
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `span.Bold` — Indicador
- `div.MobileTitle_Wrapper` — PORTUGAL
- `td` — Greve
- `div.YearCurrentText` — 2024
- `div.YearOtherText` — 1986

### Most repeated blocks (page furniture)

- `td.ValueCell` ×222 — 363
- `td.YearCell` ×39 — 1986
- `span.SymbolCaption` ×36 — ┴
- `a` ×22 — Sobre estes dados
- `span` ×17 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `b` ×9 — Setores de atividade económica
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos

## europa/2330

*População em risco de pobreza ou exclusão social: total e por sexo (percentagem)*

- selected as: median of 635 pages with markers Entidades+Fontes+ltima actualiza
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 175,774 bytes, 32 distinct tag/class groups

### Questions found on the page

- none matched

### One-of-a-kind blocks (candidate fields)

- `h1` — População em risco de pobreza ou exclusão social: total e por sexo (%)
- `div.DataSourceLegend` — Fontes/Entidades: Eurostat | Entidades Nacionais, PORDATA
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `td` — Proporção - %
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — EUROPA

### Most repeated blocks (page furniture)

- `span` ×20 — Metainformação
- `a` ×20 — Sobre estes dados
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `option` ×13 — 2025
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Que países têm maior e menor percentagem de homens ou mulheres com rendimentos i
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## municipios/791

*Índice de hierarquia de gestão dos resíduos urbanos*

- selected as: median of 421 pages with markers Entidades+Fontes+Unidade+ltima actualiza
- markers stored at harvest: `Entidades+Fontes+Unidade+ltima actualiza`
- status 200, 307,236 bytes, 30 distinct tag/class groups

### Questions found on the page

- `h2` — Onde é maior e menor o nível de aplicação da hierarquia dos resíduos na gestão do lixo urbano - máxima reciclagem, zero incineração e zero aterro?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — Índice de hierarquia de gestão dos resíduos urbanos
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `td` — Número Índice - %
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS

### Most repeated blocks (page furniture)

- `a` ×23 — Sobre estes dados
- `span` ×17 — Metainformação
- `option` ×17 — 2024
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde é maior e menor o nível de aplicação da hierarquia dos resíduos na gestão d
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## portugal/40

*População desempregada: total e por grupo etário*

- selected as: median of 140 pages with markers Entidades+Fontes+ltima actualiza+revis
- markers stored at harvest: `Entidades+Fontes+ltima actualiza+revis`
- status 200, 184,138 bytes, 34 distinct tag/class groups

### Questions found on the page

- `h2` — Quantas pessoas estão à procura de emprego, por faixa etária?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — População desempregada: total e por grupo etário
- `div.Text_Note` — A carregar conteúdo...
- `td` — Indivíduo - Milhares
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `span.Bold` — Indicador
- `div.MobileTitle_Wrapper` — PORTUGAL
- `div.YearCurrentText` — 2025
- `div.YearOtherText` — 1974

### Most repeated blocks (page furniture)

- `td.ValueCell` ×208 — 66,5
- `td.YearCell` ×52 — 1974
- `a` ×23 — Sobre estes dados
- `span` ×19 — Metainformação
- `span.SymbolCaption` ×16 — ┴
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Quantas pessoas estão à procura de emprego, por faixa etária?

## municipios/485

*Consumo de gás natural por habitante*

- selected as: median of 71 pages with markers Entidades+Fontes+Unidade+ltima actualiza+revis
- markers stored at harvest: `Entidades+Fontes+Unidade+ltima actualiza+revis`
- status 200, 290,892 bytes, 30 distinct tag/class groups

### Questions found on the page

- `h2` — Onde se utiliza, em média, por pessoa, mais e menos gás natural?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — Consumo de gás natural por habitante
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS
- `td` — Rácio

### Most repeated blocks (page furniture)

- `a` ×24 — Sobre estes dados
- `span` ×17 — Metainformação
- `option` ×17 — 2024
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde se utiliza, em média, por pessoa, mais e menos gás natural?
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## municipios/990

*Empresas individuais não financeiras: total e por setor de atividade económica*

- selected as: median of 11 pages with markers Entidades+Fontes+ltima actualiza
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 551,321 bytes, 29 distinct tag/class groups

### Questions found on the page

- `h2` — Onde há mais e menos empresários em nome individual e trabalhadores independentes na agricultura, indústria, comércio ou outros serviços?

### One-of-a-kind blocks (candidate fields)

- `h1` — Empresas individuais não financeiras: total e por setor de atividade económica
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS
- `td` — Empresa

### Most repeated blocks (page furniture)

- `option` ×33 — 2024
- `a` ×22 — Sobre estes dados
- `span` ×17 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde há mais e menos empresários em nome individual e trabalhadores independente
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## europa/1481

*Emissões de gases com efeito de estufa: total e por alguns setores de emissões de gases*

- selected as: median of 3 pages with markers Entidades+Fontes+ltima actualiza+revis
- markers stored at harvest: `Entidades+Fontes+ltima actualiza+revis`
- status 200, 181,422 bytes, 33 distinct tag/class groups

### Questions found on the page

- none matched

### One-of-a-kind blocks (candidate fields)

- `h1` — Emissões de gases com efeito de estufa: total e por alguns setores de emissões de gases
- `div.DataSourceLegend` — Fontes/Entidades: Eurostat | AEA | JRC | ETC/ACC | DG CLIMA, PORDATA
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — EUROPA

### Most repeated blocks (page furniture)

- `option` ×41 — 2024
- `span` ×29 — Metainformação
- `a` ×25 — Sobre estes dados
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Em que que países há mais e menos emissões de dióxido de carbono e outros gases 
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## portugal/2958

*Despesa corrente em cuidados de saúde: total e por tipo de prestador*

- selected as: median of 2 pages with markers Entidades+Fontes+Unidade+ltima actualiza
- markers stored at harvest: `Entidades+Fontes+Unidade+ltima actualiza`
- status 200, 186,216 bytes, 35 distinct tag/class groups

### Questions found on the page

- `h2` — Quanto gastam em saúde os hospitais, estabelecimentos de enfermagem, cuidados residenciais especializados, entre outros?

### One-of-a-kind blocks (candidate fields)

- `h1` — Despesa corrente em cuidados de saúde: total e por tipo de prestador
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `td` — Euro - Milhares
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `span.Bold` — Indicador
- `div.MobileTitle_Wrapper` — PORTUGAL
- `div.YearCurrentText` — 2024
- `div.YearOtherText` — 2000

### Most repeated blocks (page furniture)

- `td.ValueCell` ×250 — <number>
- `td.YearCell` ×25 — 2000
- `a` ×22 — Sobre estes dados
- `span` ×17 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `span.SymbolCaption` ×11 — Pro
- `b` ×11 — Tipo de prestador
- `option` ×10 — Total Tipo de prestador
- `div` ×10 — Operações

## municipios/136

*População residente, estimativas a 31 de dezembro: total e por sexo*

- selected as: median of 1 pages with markers Entidades+Fontes+ltima actualiza+revis
- markers stored at harvest: `Entidades+Fontes+ltima actualiza+revis`
- status 200, 486,072 bytes, 29 distinct tag/class groups

### Questions found on the page

- `h2` — Onde há mais e menos homens ou mulheres no final de cada ano?

### One-of-a-kind blocks (candidate fields)

- `h1` — População residente, estimativas a 31 de dezembro: total e por sexo
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS
- `td` — Indivíduo

### Most repeated blocks (page furniture)

- `option` ×22 — 2025
- `a` ×19 — Sobre estes dados
- `span` ×15 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde há mais e menos homens ou mulheres no final de cada ano?
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## europa/2489

*Evolução da Superfície por Países*

- selected as: smallest europa page (165,272 B)
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 165,271 bytes, 32 distinct tag/class groups

### Questions found on the page

- `h2` — Que países da Europa têm maior e menor área?

### One-of-a-kind blocks (candidate fields)

- `div.DataSourceLegend` — Fontes/Entidades: Eurostat | Institutos Nacionais de Estatística, PORDATA
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `h1` — Superfície
- `div.MobileTitle_Wrapper` — EUROPA
- `td` — Km²

### Most repeated blocks (page furniture)

- `option` ×37 — 2026
- `span` ×18 — Metainformação
- `a` ×18 — Sobre estes dados
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Que países da Europa têm maior e menor área?
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## europa/1443

*Patentes concedidas pelo Gabinete de Patentes e Marcas dos EUA (USPTO): total e por secções da Classificação Internacional de Patentes (CIP) (1977-2010)*

- selected as: largest europa page (188,710 B)
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 188,710 bytes, 33 distinct tag/class groups

### Questions found on the page

- `h2` — Que países requerem mais e menos a patente nos EUA de invenções relacionadas, por exemplo, com necessidades humanas, técnicas industriais, transportes, física, eletricidade ou engenharia?

### One-of-a-kind blocks (candidate fields)

- `h1` — Patentes concedidas pelo Gabinete de Patentes e Marcas dos EUA (USPTO): total e por secções da Classificação Internacional de Patentes (CIP) (1977-201
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.DataSourceLegend` — Fontes/Entidades: Eurostat | EPO, PORDATA
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `td` — Registos
- `div.MobileTitle_Wrapper` — EUROPA
- `span.SymbolCaption` — Pro

### Most repeated blocks (page furniture)

- `option` ×42 — 2010
- `a` ×22 — Sobre estes dados
- `span` ×19 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Que países requerem mais e menos a patente nos EUA de invenções relacionadas, po
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## municipios/855

*População ativa por inativa*

- selected as: smallest municipios page (174,272 B)
- markers stored at harvest: `Entidades+Fontes+Unidade+ltima actualiza`
- status 200, 174,272 bytes, 30 distinct tag/class groups

### Questions found on the page

- `h2` — Onde há mais e menos ativos, em média, por pessoa que não está empregada nem desempregada?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — População ativa por inativa
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS
- `td` — Rácio

### Most repeated blocks (page furniture)

- `a` ×19 — Sobre estes dados
- `option` ×18 — 2025
- `span` ×15 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde há mais e menos ativos, em média, por pessoa que não está empregada nem des
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## municipios/358

*População residente: total e por grupo etário*

- selected as: largest municipios page (2,208,230 B)
- markers stored at harvest: `Entidades+Fontes+Unidade+ltima actualiza+revis`
- status 200, 2,208,230 bytes, 30 distinct tag/class groups

### Questions found on the page

- `h2` — Onde há mais e menos pessoas, por idades?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — População residente: total e por grupo etário
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `div.MobileTitle_Wrapper` — MUNICÍPIOS
- `td` — Indivíduo

### Most repeated blocks (page furniture)

- `option` ×43 — 2025
- `a` ×24 — Sobre estes dados
- `span` ×17 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×11 — Todos
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Onde há mais e menos pessoas, por idades?
- `div.body-xs-regular` ×6 — Morada
- `div.Header_Menu_Mobile_Item_Label` ×5 — Estatísticas

## portugal/3748

*Áreas Protegidas e Rede Natura 2000 (percentagem)*

- selected as: smallest portugal page (164,275 B)
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 164,276 bytes, 36 distinct tag/class groups

### Questions found on the page

- `h2` — Qual a percentagem de superfície ocupada por habitats naturais protegidos pelas leis nacionais, as Áreas Protegidas, e pela União Europeia, a Rede Natura 2000?

### One-of-a-kind blocks (candidate fields)

- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `h1` — Áreas Protegidas e Rede Natura 2000 (%)
- `option` — Áreas Protegidas e Rede Natura 2000
- `div.NonTotalContainer2` — Áreas Protegidas e Rede Natura 2000
- `b` — Áreas Protegidas e Rede Natura 2000
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `td` — Proporção - %
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `span.Bold` — Indicador
- `div.MobileTitle_Wrapper` — PORTUGAL
- `div.YearCurrentText` — 2024
- `div.YearOtherText` — 2011
- `span.SymbolCaption` — ┴

### Most repeated blocks (page furniture)

- `a` ×18 — Sobre estes dados
- `span` ×15 — Metainformação
- `td.YearCell` ×14 — 2011
- `td.ValueCell` ×14 — 22,3
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações
- `span.body-xs-bold` ×8 — Fundação Francisco Manuel dos Santos
- `h2` ×7 — Qual a percentagem de superfície ocupada por habitats naturais protegidos pelas 
- `div.body-xs-regular` ×6 — Morada

## portugal/2611

*Dormidas nos alojamentos turísticos: total e por país de residência do hóspede*

- selected as: largest portugal page (282,124 B)
- markers stored at harvest: `Entidades+Fontes+ltima actualiza`
- status 200, 282,125 bytes, 35 distinct tag/class groups

### Questions found on the page

- `h2` — Quantas noites passam os turistas em estabelecimentos hoteleiros como hotéis e pousadas, por país de origem?

### One-of-a-kind blocks (candidate fields)

- `h1` — Dormidas nos alojamentos turísticos: total e por país de residência do hóspede
- `div.NewLanding_InfoText` — Aprofunde a sua análise. Veja e compare dados e anos.
- `div.Text_Note` — A carregar conteúdo...
- `div.NewLanding_MoreDataButton` — Mais opções e dados
- `a.Header_Menu_Mobile_Item_Label` — Atualizações
- `div.Header_Menu_Item_New` — Atualizações
- `div.Feedback_AjaxWait` — Carregando
- `span.Bold` — Indicador
- `div.MobileTitle_Wrapper` — PORTUGAL
- `td` — Dormida
- `div.YearCurrentText` — 2025
- `div.YearOtherText` — 1964

### Most repeated blocks (page furniture)

- `td.ValueCell` ×1225 — <number>
- `span.SymbolCaption` ×569 — x
- `td.YearCell` ×66 — 1960
- `b` ×30 — País de residência
- `option` ×26 — Total País de residência
- `a` ×22 — Sobre estes dados
- `span` ×17 — Metainformação
- `a.Header_Menu_Mobile_SubItem_New` ×13 — Portugal
- `div.Header_Menu_SubItem_New` ×13 — Portugal
- `div` ×10 — Operações

