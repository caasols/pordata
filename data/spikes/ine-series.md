# Spike: the shape of an INE series (roadmap 14)

The crosswalk hands item 14 a `varcd`; nobody had fetched one. Item 14's three open questions — size, vintages, and how to render "no series" — are all unanswerable in the abstract, so this looks at real responses.

**Measurement, not archiving.** No value fetched here is committed: bodies go to the workflow artifact and only the shape reaches the repo. That is what lets this run before item 13 records INE's reuse terms.

**Confound, recorded:** 8 requests to INE on this date (of 8 planned; the run stops after 3 consecutive refusals). The licence spike already got 403 from www.ine.pt on this same runner today, so this date was not clean before this ran. Item 22 samples availability once a day to characterise INE's block; its reading for this day inherits this traffic and should not be treated as a clean sample.

## Responses

| row | varcd | status | KB | parsed | key paths |
|---|---|---|---|---|---|
| `municipios/1` | `0009598` | 200 | 291.0 | yes | 17 |
| `municipios/366` | `0008264` | 200 | 40.3 | yes | 15 |
| `municipios/817` | `0007001` | 200 | 0.4 | yes | 7 |
| `portugal/1105` | `0012770` | 200 | 307.4 | yes | 17 |
| `portugal/2380` | `0008014` | 200 | 2.2 | yes | 15 |
| `portugal/2885` | `0006566` | 200 | 867.6 | yes | 17 |
| `portugal/3250` | `0008368` | 200 | 10439.6 | yes | 21 |
| `portugal/3437` | `0000058` | 200 | 28.7 | yes | 19 |

## Size

- median **291.0 KB**, max **10439.6 KB** across 8 series
- extrapolated over the crosswalk's 1,062 named ids: **~1553 MB** raw

That is the number item 14's first open question wanted: it decides whether the archive lives next to `catalogue.json` in git or needs different storage.

## Schema

Key paths from the first parsed response, so the long-format target schema (indicator, geography, period, value, unit, flag) can be mapped rather than invented:

```
[].Dados
[].Dados.2023
[].Dados.2023[].dim_3
[].Dados.2023[].dim_3_t
[].Dados.2023[].geocod
[].Dados.2023[].geodsg
[].Dados.2023[].ind_string
[].Dados.2023[].valor
[].DataExtracao
[].DataUltimoAtualizacao
[].IndicadorCod
[].IndicadorDsg
[].MetaInfUrl
[].Sucesso
[].Sucesso.Verdadeiro
[].Sucesso.Verdadeiro[].Msg
[].UltimoPref
```

Keys that look like the dimensions we need:

- `[].IndicadorDsg`
- `[].Dados.2023[].geocod`
- `[].Dados.2023[].geodsg`
- `[].Dados.2023[].dim_3`
- `[].Dados.2023[].dim_3_t`
- `[].Dados.2023[].valor`
