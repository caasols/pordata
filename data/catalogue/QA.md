# Catalogue QA

Records: 1388 (1387 ok, 1 errored)

## Field coverage (% non-empty)

| area | n | name | description | fontes | ultima_atualizacao | json_ld |
|---|---|---|---|---|---|---|
| europa | 638 | 99% | 99% | 100% | 100% | 100% |
| municipios | 504 | 99% | 99% | 100% | 100% | 100% |
| portugal | 245 | 100% | 100% | 100% | 100% | 100% |
| ALL | 1387 | 99% | 99% | 100% | 100% | 100% |

## Findings

- duplicate ids: [16, 56, 57, 58, 60, 99, 100, 108, 109, 112, 116, 117, 118, 245, 256, 267, 268, 313, 320, 326]
- empty name: 3
  - `financiamento+da+uniao+europeia+aos+paises+em+desenvolvimento-3597`
  - `taxa+de+atividade+total+e+por+grupo+etario-3828`
  - `votos+validos+na+eleicao+para+a+assembleia+legislativa+da+regiao+auton`
- fontes contains UI boundary text (over-capture; repair in 3d pass): 8
  - `abastecimento+publico+de+agua-1415`
  - `abortos+interrupcoes+voluntarias+de+gravidez-3393`
  - `absolvidos-3308`
  - `acidentes+de+trabalho+graves+e+mortais-1355`
  - `acidentes+de+trabalho+graves+total+e+por+alguns+setores+de+atividade+e`
  - `acidentes+de+trabalho+mortais+por+100+mil+empregados+total+e+por+sexo-`
  - `acidentes+de+trabalho+mortais+total+e+por+alguns+setores+de+atividade+`
  - `acidentes+de+trabalho+mortais+total+e+por+sexo-1325`

## Error records (will be retried next run)

- `portugal/despesas+das+administracoes+publicas+em+ambiente+em+percentagem+do+tota`: HTTP Error 500: Internal Server Error
