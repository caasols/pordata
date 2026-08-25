# Where PORDATA is thin against INE — a shortlist to accept or reject

Rebuilt by `scripts/coverage_gap.py`. **This is a selection, not an inventory.** The goal is to be more complete than PORDATA, and the way to fail at it is to add coverage without curation: every entry that lands needs a human-meaningful Portuguese name, a theme and a stated reason for being there. Accepting or rejecting the rows below one by one is what produces the curation rule — there is no honest shortcut to one.

## What this does not claim

The **series-level** complement is not computable and is not attempted. The crosswalk names 1069 of 13084 INE ids (8.2%) because it refuses rather than guesses, so subtracting it from INE's catalogue would present some twelve thousand series as "missing" when most are indicators PORDATA covers under a name the matcher declines to claim. That number would be enormous, precise and wrong.

The unit here is the **concept**: a content word INE uses that none of PORDATA's 2196 indicator names uses once (2687 distinct words, PT and EN). That question survives a matcher with a quarter of the recall, because it asks whether PORDATA has *any* indicator touching a subject.

Ranked by how many **distinct** INE indicators use the word, not by series count: INE republishes one title across geographies and vintages, so a series count measures how widely a title was cut rather than how much INE has to say. Distinct titles are its own investment in the subject, the closest thing to demand available before the ledger (item 3) exists. Floor of 8 series; 302 concepts clear it, and the 40 largest are below.

### Inovação e conhecimento / Sociedade da informação

- **`encomendas`** (with `cento`, `receber`) — 80 distinct INE indicators (118 series), 60% in this subtheme; published down to Continente, NUTS I, NUTS II
  - Encomendas a fornecedores estrangeiros (%) do comércio
  - Índice de novas encomendas na indústria - bruto (Base - 2000)
  - Índice de novas encomendas na construção e obras públicas (Base - 2000)
- **`individuo`** — 35 distinct INE indicators (99 series), 90% in this subtheme; published down to Freguesia, Município, NUTS II
  - Despesas da proteção social em pensões por indivíduo ativo (€)
  - Volume de trabalho da população agrícola familiar por indivíduo (UTA)
  - Horas efetivamente trabalhadas no ano (h) pelo individuo nas organizações patronais
- **`fins`** (with `lucrativos`, `interagiram`) — 35 distinct INE indicators (81 series), 70% in this subtheme; published down to Continente, Município, NUTS II
  - Despesa consolidada em ambiente (€) das instituições sem fins lucrativos
  - Despesa em investigação e desenvolvimento (I&D - €) das instituições privadas sem fins lucrativos
  - Proporção de estabelecimentos de ensino não superior com acesso à internet para fins pedagógicos (%)
- **`televisao`** (with `tdt`, `subscricao`, `televisores`) — 26 distinct INE indicators (72 series), 94% in this subtheme; published down to Município, NUTS II, Portugal
  - Assinantes do serviço de televisão através de subscrição (N.º)
  - Assinantes do serviço de televisão através de subscrição por 100 alojamentos familiares clássicos (%)
  - Televisores ligados à Televisão Digital Terrestre (TDT) em casa de agregados domésticos privados (N.º)
- **`terrestre`** — 26 distinct INE indicators (63 series), 86% in this subtheme; published down to Continente, Município, NUTS 2
  - Assinantes do serviço móvel terrestre (N.º)
  - Superfície terrestre (km² - COS - Série 1) das unidades territoriais
  - Superfície terrestre (km² - COS - Série 2) das unidades territoriais
- **`disponibilizam`** — 23 distinct INE indicators (29 series), 100% in this subtheme; published down to NUTS I, NUTS III, Portugal
  - Câmaras Municipais que disponibilizam aplicações móveis ao utente (N.º)
  - Proporção de Câmaras Municipais que disponibilizam aplicações móveis ao utente (%)
  - Proporção de hospitais que disponibilizam acesso a computadores aos doentes internados (%)
- **`efetuaram`** (with `encomendados`) — 21 distinct INE indicators (36 series), 94% in this subtheme; published down to Continente, Município, NUTS I
  - Proporção de explorações agrícolas que efetuaram análises de terras nos últimos 3 anos (%)
  - Proporção de hospitais que efetuaram encomendas de bens e/ou serviços através da Internet (%)
  - Proporção de hospitais que não efetuaram encomendas de bens e/ou serviços através da Internet (%)

### Educação, formação e aprendizagem / Formação

- **`participaram`** — 21 distinct INE indicators (194 series), 99% in this subtheme; published down to Município, NUTS II, Portugal
  - Indivíduos com idade entre 18 e 64 anos que participaram em atividades de educação formal (N.º)
  - Indivíduos com idade entre 18 e 64 anos que participaram em atividades de educação não formal (N.º)
  - Indivíduos com idade entre 18 e 64 anos que participaram em atividades de aprendizagem informal (N.º)
- **`formal`** — 21 distinct INE indicators (105 series), 100% in this subtheme; published down to NUTS II, Portugal
  - Tempo despendido por participante em atividades de educação formal (h)
  - Tempo despendido por participante em atividades de educação não formal (h)
  - Despesa por participante em propinas e livros em atividades de educação formal (€)

### Inovação e conhecimento / Ciência e tecnologia

- **`inovacao`** (with `cooperacao`, `melhorados`) — 50 distinct INE indicators (280 series), 99% in this subtheme; published down to NUTS II, Portugal, Região
  - Proporção de empresas com 10 e mais pessoas ao serviço com atividades de inovação (%)
  - Intensidade de inovação das empresas com 10 e mais pessoas ao serviço com atividades de inovação (%)
  - Proporção de empresas com atividades de inovação com 10 e mais pessoas ao serviço com inovação de produto (%)

### Saúde / Mortalidade por causas de morte

- **`potenciais`** — 74 distinct INE indicators (79 series), 100% in this subtheme; published down to NUTS II, NUTS III
  - Anos potenciais de vida perdidos (Ano)
  - Anos potenciais de vida perdidos por pneumonia (Anos)
  - Número médio de anos potenciais de vida perdidos (Ano)
- **`doencas`** (with `circulatorio`) — 54 distinct INE indicators (59 series), 80% in this subtheme; published down to Distrito, Município, NUTS II
  - Taxa de mortalidade por doenças do aparelho circulatório (‰)
  - População residente com menos de 15 anos sem doenças do sangue (N.º)
  - Anos potenciais de vida perdidos por doenças cerebrovasculares (Anos)
- **`maligno`** (with `tumor`, `bronquios`, `pulmao`) — 54 distinct INE indicators (54 series), 100% in this subtheme; published down to NUTS II
  - Anos potenciais de vida perdidos por tumor maligno da próstata (Anos)
  - Anos potenciais de vida perdidos por tumor maligno do estômago (Anos)
  - Anos potenciais de vida perdidos por tumor maligno do pâncreas (Anos)
- **`malignos`** (with `tumores`, `orgaos`) — 44 distinct INE indicators (47 series), 100% in this subtheme; published down to Município, NUTS II, Portugal
  - Taxa de mortalidade por tumores malignos (‰)
  - Anos potenciais de vida perdidos por tumores malignos (Anos)
  - Taxa de mortalidade por tumores malignos por 100 000 habitantes (N.º)
- **`aparelho`** (with `digestivo`, `respiratorio`) — 32 distinct INE indicators (35 series), 100% in this subtheme; published down to Município, NUTS II, Portugal
  - Taxa de mortalidade por doenças do aparelho circulatório (‰)
  - Anos potenciais de vida perdidos por doenças do aparelho digestivo (Anos)
  - Anos potenciais de vida perdidos por doenças do aparelho circulatório (Anos)

### Conjuntura / Mercado de trabalho

- **`horas`** (with `trabalhadas`) — 130 distinct INE indicators (193 series), 67% in this subtheme; published down to Município, Portugal
  - Incêndios rurais com duração superior a 24 horas (N.º)
  - Índice de horas trabalhadas no comércio - bruto (Base - 2021)
  - Índice de horas trabalhadas na indústria - bruto (Base - 2000)

### Conjuntura / Oferta de bens e serviços

- **`apreciacao`** — 44 distinct INE indicators (44 series), 46% in this subtheme; published down to Portugal, Total
  - Apreciação sobre a atividade (Saldo de respostas extremas) do comércio
  - Apreciação sobre volume de vendas (Saldo de respostas extremas) do comércio
  - Apreciação sobre o volume de stocks (Saldo de respostas extremas) do comércio
- **`proximos`** (with `perspetivas`) — 36 distinct INE indicators (36 series), 31% in this subtheme; published down to Portugal
  - Perspetivas sobre o emprego nos próximos 3 meses (Saldo de respostas extremas) do comércio
  - Perspetivas sobre a procura nos próximos 3 meses (Saldo de respostas extremas) dos serviços
  - Perspetivas sobre o emprego nos próximos 3 meses (Saldo de respostas extremas) dos serviços
- **`externo`** — 35 distinct INE indicators (62 series), 47% in this subtheme; published down to Portugal
  - Índice de novas encomendas na indústria no mercado externo - bruto (Base - 2000)
  - Índices de preços na produção industrial no mercado externo - bruto (Base - 2015)
  - Índice de volume de negócios na indústria no mercado externo - bruto (Base - 2000)

### Proteção social / Regime da segurança social

- **`beneficiarias`** — 44 distinct INE indicators (81 series), 94% in this subtheme; published down to Município, NUTS II, Portugal
  - Beneficiárias/os do subsídio por morte da segurança social (N.º)
  - Beneficiárias/os de licença por adoção, da segurança social (N.º)
  - Beneficiárias/os do subsídio de funeral da segurança social (N.º)
- **`licenca`** — 38 distinct INE indicators (45 series), 100% in this subtheme; published down to Município, NUTS II, Portugal
  - Duração da licença por adoção, da segurança social (Dia)
  - Duração da licença parental inicial, da segurança social (Dia)
  - Duração da licença parental alargada, da segurança social (Dia)

### Conjuntura / Procura de bens e serviços

- **`extremas`** (with `respostas`, `perspetiva`) — 71 distinct INE indicators (71 series), 42% in this subtheme; published down to Portugal
  - Indicador de confiança (Saldo de respostas extremas) do comércio
  - Indicador de confiança (Saldo de respostas extremas) dos serviços
  - Indicador de confiança (Saldo de respostas extremas) da construção
- **`indicador`** (with `confianca`) — 30 distinct INE indicators (36 series), 42% in this subtheme; published down to Município, Portugal, União Europeia
  - Indicador de clima económico (%)
  - Indicador de confiança (Saldo de respostas extremas) do comércio
  - Indicador de risco harmonizado 1 do uso de pesticidas (IRH1) (-)

### Mercado de trabalho / Custo do trabalho

- **`custo`** (with `nova`) — 39 distinct INE indicators (96 series), 54% in this subtheme; published down to Continente, NUTS II, NUTS III
  - Índice de custo do trabalho (Base - 2008)
  - Custo das mercadorias vendidas (€) das Empresas
  - Custo de suportes publicitários (€) das Empresas

### População / Censos da população

- **`nucleos`** (with `casais`, `reconstituidos`) — 25 distinct INE indicators (84 series), 100% in this subtheme; published down to Freguesia
  - Núcleos familiares (N.º)
  - Núcleos familiares (N.º) de casais
  - Núcleos familiares conjugais (N.º)

### Construção e habitação / Outros indicadores da construção e habitação

- **`contratos`** (with `arrendamento`, `hipoteca`, `voluntaria`) — 34 distinct INE indicators (82 series), 72% in this subtheme; published down to Freguesia, Município, NUTS I
  - Contratos de compra e venda (€) de prédios
  - Contratos de compra e venda (N.º) de prédios
  - Contratos de mútuo com hipoteca voluntária (€)

### Empresas / Filiais de empresas estrangeiras

- **`estrangeiras`** (with `maioritariamente`) — 47 distinct INE indicators (68 series), 84% in this subtheme; published down to NUTS II, NUTS III, Portugal
  - Empresas maioritariamente estrangeiras (N.º)
  - Proporção de empresas maioritariamente estrangeiras (%)
  - Empresas maioritariamente estrangeiras (Série 2005-2007 - N.º)

### Comércio interno / Comércio interno

- **`relevante`** (with `dedicadas`, `marca`, `predominancia`) — 28 distinct INE indicators (62 series), 97% in this subtheme; published down to Continente, NUTS II, Portugal
  - Unidades comerciais de dimensão relevante (N.º)
  - Unidades comerciais de dimensão relevante (Série 2004-2010 - N.º)
  - Volume de vendas (€) das unidades comerciais de dimensão relevante

### Território / Ordenamento do território

- **`declarado`** (with `deduzido`, `sujeitos`, `p10`, `p20`) — 40 distinct INE indicators (61 series), 100% in this subtheme; published down to Freguesia, Município
  - Rendimento bruto declarado (€)
  - Rendimento bruto declarado por habitante (€)
  - Rendimento bruto declarado por agregado fiscal (€)

### Educação, formação e aprendizagem / Alunos

- **`alunas`** (with `matriculadas`) — 19 distinct INE indicators (55 series), 98% in this subtheme; published down to Município, NUTS II, NUTS III
  - Alunas/os inscritas/os no ensino superior (N.º)
  - Alunas/os matriculadas/os no ensino não superior (N.º)
  - Alunas/os inscritas/os por docente do ensino superior (N.º)

### Saúde / Estado de saúde e cuidados de saúde autorreferidos

- **`referiu`** — 20 distinct INE indicators (44 series), 80% in this subtheme; published down to NUTS II, Portugal
  - População residente com 15 e mais anos que referiu sofrer de diabetes (N.º)
  - População residente com 15 e mais anos que referiu sofrer de depressão (N.º)
  - População residente com 15 e mais anos que referiu sofrer de hipertensão arterial (N.º)

### População / Projeções de população

- **`projecoes`** — 40 distinct INE indicators (40 series), 100% in this subtheme; published down to NUTS II
  - Saldo migratório (projeções 2012-2060 - N.º)
  - Saldo migratório (projeções 2015-2080 - N.º)
  - Saldo migratório (projeções 2018-2080 - N.º)

### Comércio internacional / Comércio intra-UE

- **`intra`** — 26 distinct INE indicators (40 series), 35% in this subtheme; published down to NUTS II, NUTS III, Portugal
  - Empresas Intra-UE exportadoras de bens (€)
  - Empresas Intra-UE importadoras de bens (€)
  - Proporção de exportações de bens intra-UE (%)

### Agricultura, floresta e pescas / Balanços de aprovisionamento

- **`grau`** (with `autoaprovisionamento`) — 29 distinct INE indicators (37 series), 60% in this subtheme; published down to Freguesia, NUTS II, NUTS III
  - Grau de abertura (%)
  - Grau de autoaprovisionamento de mel (%)
  - Grau de autoaprovisionamento de ovos (%)

### Ambiente / Ar e clima

- **`normal`** (with `desvio`, `desloca`) — 26 distinct INE indicators (37 series), 60% in this subtheme; published down to Continente, Estação meteorológica, NUTS III
  - Desvio em relação à normal da temperatura média do ar (°C)
  - Desvio em relação à normal da temperatura máxima do ar (°C)
  - Desvio em relação à normal da temperatura mínima do ar (°C)

### Indústria e energia / Energia

- **`tep`** — 21 distinct INE indicators (34 series), 100% in this subtheme; published down to Município, NUTS I, NUTS II
  - Consumo final de energia (tep)
  - Consumo de energia primária (tep)
  - Importação de energia primária (tep)

### Preços / Preços na produção

- **`meios`** — 19 distinct INE indicators (30 series), 67% in this subtheme; published down to Continente, NUTS I, NUTS III
  - Índice de preços dos meios de produção na agricultura (Base - 2000)
  - Proporção de hospitais que utilizam meios informáticos nas atividades desenvolvidas (%)
  - Índice de preços dos meios de produção na agricultura (Taxa de variação mensal - Base 2000 - %)

### Contas nacionais e regionais / Contas regionais

- **`dispersao`** (with `nuts`) — 23 distinct INE indicators (26 series), 31% in this subtheme; published down to Portugal
  - Dispersão regional do PIB por habitante (Base 2011, NUTS 2002 - %)
  - Dispersão regional do PIB por habitante (Base 2011, NUTS 2013 - %)
  - Dispersão regional do PIB por habitante (Base 2016, NUTS 2013 - %)

### Transportes e comunicações / Transportes terrestres

- **`exploradoras`** (with `pesado`) — 19 distinct INE indicators (22 series), 100% in this subtheme; published down to NUTS 2, NUTS II, Portugal
  - Vagões (N.º) das empresas exploradoras de sistema ferroviário pesado
  - Pessoal ao serviço (N.º) nas empresas exploradoras de sistema ferroviário ligeiro
  - Material circulante (N.º) das empresas exploradoras de sistema ferroviário ligeiro

### Proteção social / Receitas e despesas da proteção social

- **`pibpm`** — 19 distinct INE indicators (19 series), 100% in this subtheme; published down to Portugal
  - Despesas da proteção social (% do PIBpm - Base 2000)
  - Despesas da proteção social (% do PIBpm - Base 2006)
  - Despesas da proteção social (% do PIBpm - Base 2011)

## What was filtered out, and why

INE writes bookkeeping into its titles — vintages, classification versions, seasonal adjustment, survey reference periods. Those words are absent from PORDATA because they are not subjects, and they dominate the raw list. Removing them is a judgement, so here it is in the open:

- `serie` — 860 indicators / 1869 series — e.g. Água captada (Série 2011 - m³)
- `homologa` — 256 indicators / 324 series — e.g. Taxa de variação homóloga do PIB (Base 2006 - %)
- `ajustado` — 244 indicators / 382 series — e.g. Índice de custo do trabalho (ajustado de dias úteis, Base - 2008)
- `sazonalidade` — 152 indicators / 214 series — e.g. Subutilização do trabalho (Ajustada de sazonalidade - N.º)
- `cae` — 151 indicators / 511 series — e.g. Emprego cultural (Série 2021, CAE Rev. 3 - N.º)
- `hab` — 75 indicators / 121 series — e.g. Pegada material per capita (t/ hab.)
- `trimestrais` — 61 indicators / 61 series — e.g. Turistas (Trimestrais - N.º)
- `deflacionado` — 59 indicators / 68 series — e.g. Índice de volume de negócios no comércio - bruto deflacionado (Base - 2021)
- `metodologia` — 55 indicators / 185 series — e.g. Ecrãs de cinema (Metodologia 2006 - N.º)
- `trimestral` — 50 indicators / 57 series — e.g. Índice de preços da habitação (Taxa de variação trimestral - Base 2015 - %)
- `entrevista` — 32 indicators / 94 series — e.g. População empregada que teve consulta ou exames de Medicina do Trabalho nos dois anos anteriores à entrevista
- `primeiros` — 28 indicators / 78 series — e.g. Proporção de primeiros casamentos (%)

If any of these is a subject rather than an annotation, take it out of `ANNOTATION` in `scripts/coverage_gap.py` and it rejoins the shortlist.
