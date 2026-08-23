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
- name/description carries inline HTML (stripped at build): 25
  - `administracoes+publicas+despesa+em+tribunais+per+capita-3590`
  - `apoio+do+governo+a+investigacao+e+desenvolvimento+(i+d)+na+agricultura`
  - `consumo+de+energia+final+das+familias+per+capita-3551`
  - `emissao+media+de+co2+por+km+dos+automoveis+novos+de+passageiros-3611`
  - `emissoes+de+gases+com+efeito+de+estufa+per+capita-3360`
  - `empresas+com+10+e+mais+pessoas+ao+servico+com+website+ou+homepage+em+p`
  - `empresas+com+10+e+mais+pessoas+ao+servico+com+website+ou+homepage+em+p`
  - `pegada+material+per+capita-3745`

## Error records (will be retried next run)

- `portugal/despesas+das+administracoes+publicas+em+ambiente+em+percentagem+do+tota`: HTTP Error 500: Internal Server Error
