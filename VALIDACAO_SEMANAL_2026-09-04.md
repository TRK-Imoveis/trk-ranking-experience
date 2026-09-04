# Validação Semanal — Painel TRK
**Data:** 04/09/2026
**Status:** ✅ OK

## Resumo
O painel está atualizado (dados gerados hoje) e todos os 5 colaboradores estão presentes com notas válidas dentro da faixa 0-10. Nenhum campo crítico vazio identificado.

## Última atualização do painel
- **Data:** 2026-09-04T16:28:42Z (campo `_meta.geradoEm`; `_meta.ref` = 2026-09-04T16:04:55Z)
- **Dias desde última atualização:** 0

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 3,69 | N=4 (Com. Locação) |
| Vivianne | 7,37 | — |
| Natália | 6,35 | N=9 (Cont. ADM: 8, Renovação: 1) |
| Gardênia | 5,32 | N=4 (Cont. ADM) |
| Marinho | 6,80 | N=7 (Vistorias) |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- `_meta.etl_ultima_carga` está `null`, mas isso é esperado quando `_meta.fonte = "api"` (não houve carga via ETL nesta atualização) — não é um problema de dados.
- Delta vs. o relatório de edição mais recente encontrado (`config/relatorio_edicao_12.md`, fechado em 18/06/2026, snapshot ref 2026-06-18) — não é uma edição semanal, então a variação reflete ~2,5 meses e não uma semana:
  - Vivianne: 6,25 → 7,37 (+1,12)
  - Natália: 4,92 → 6,35 (+1,43)
  - Gardênia: 4,64 → 5,32 (+0,68)
  - Caio: 4,62 → 3,69 (−0,93)
  - Marinho: 3,90 → 6,80 (+2,90)
- Não há relatório de edição mais recente que a 12ª disponível em `config/` para uma comparação mais próxima da data atual.

---
*Gerado automaticamente pela routine Claude Code em 04/09/2026 16:39 UTC*
