# Catalogue QA

Records: 2196 (2195 ok, 1 errored)

## Field coverage (% non-empty)

| area | n | name | description | fontes | ultima_atualizacao | json_ld |
|---|---|---|---|---|---|---|
| europa | 638 | 99% | 99% | 100% | 100% | 100% |
| municipios | 504 | 99% | 99% | 100% | 100% | 100% |
| portugal | 1053 | 100% | 100% | 100% | 100% | 100% |
| ALL | 2195 | 99% | 99% | 100% | 100% | 100% |

## Findings

- duplicate ids: [5, 6, 8, 9, 10, 11, 12, 16, 25, 28, 30, 31, 32, 34, 35, 37, 38, 40, 41, 42]
- empty name: 3
  - `financiamento+da+uniao+europeia+aos+paises+em+desenvolvimento-3597`
  - `taxa+de+atividade+total+e+por+grupo+etario-3828`
  - `votos+validos+na+eleicao+para+a+assembleia+legislativa+da+regiao+auton`
- fontes contains UI boundary text (over-capture; repair in 3d pass): 512
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
