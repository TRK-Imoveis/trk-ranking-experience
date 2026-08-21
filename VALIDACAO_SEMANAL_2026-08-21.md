# Validação Semanal — Painel TRK
**Data:** 21/08/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há menos de 1 dia, com os 5 colaboradores presentes, notas dentro da faixa válida e sem campos críticos vazios.

## Última atualização do painel
- **Data:** 20/08/2026 22:01 UTC (`_meta.geradoEm`)
- **Dias desde última atualização:** < 1 dia

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,45 | N=4 |
| Vivianne | 6,95 | N=0 |
| Natália | 5,99 | N=6 |
| Gardênia | 5,45 | N=4 |
| Marinho | 5,10 | N=7 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- Delta vs. última edição fechada e auditada (12ª edição, fechamento em 18/06/2026 — não há edição mais recente fechada; os dados de `atual.json` são "live", ainda não fechados/auditados):
  - Vivianne: 6,25 → 6,95 (+0,70)
  - Natália: 4,92 → 5,99 (+1,07)
  - Gardênia: 4,64 → 5,45 (+0,81)
  - Caio: 4,62 → 4,45 (−0,17)
  - Marinho: 3,90 → 5,10 (+1,20)
- Os únicos campos `null` encontrados no JSON são `_meta.etl_ultima_carga` (esperado, pois `fonte` é `"api"`) e `scores` de categorias não aplicáveis ao cargo de cada pessoa — nenhum campo crítico vazio ou inesperado foi identificado.

---
*Gerado automaticamente pela routine Claude Code em 21/08/2026 20:10 UTC*
