# Validação Semanal — Painel TRK
**Data:** 19/06/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia (gerado em 18/06/2026). Todos os 5 colaboradores estão presentes com notas válidas entre 0 e 10. Vivianne lidera com 6,25 (+1,24 vs 11ª ed.); maior queda é de Caio (−0,72 vs 11ª ed.).

## Última atualização do painel
- **Data:** 2026-06-18T14:41:56Z
- **Dias desde última atualização:** 1 dia

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,62 | N=4 |
| Vivianne | 6,25 | N=66 |
| Natália | 4,92 | N=6 |
| Gardênia | 4,64 | N=4 |
| Marinho | 3,90 | — |

## Delta vs edição anterior (12ª vs 11ª)
| Pessoa | Nota 12ª | Nota 11ª | Δ |
|---|---:|---:|---:|
| Vivianne | 6,25 | 5,01 | +1,24 |
| Natália | 4,92 | 4,02 | +0,90 |
| Gardênia | 4,64 | 4,10 | +0,54 |
| Caio | 4,62 | 5,34 | −0,72 |
| Marinho | 3,90 | 3,91 | −0,01 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- **Mudança de liderança (12ª ed.):** Vivianne assume o 1º lugar; Caio cai de 1º para 4º. Causas documentadas no `config/relatorio_edicao_12.md` (sem OFFs de modelo).
- **Marinho (3,90):** apenas 2 indicadores ativos — Laudos ≤24h: 36/53 (67,9%) e Contestações <24h: 1/10 (10%). Contestações é o ponto crítico.
- **`bonus_proc: null` do Marinho** é esperado — bônus = 0 nesta edição.
- **Pendência em aberto (da 12ª ed.):** corrigir `atualizar_painel.ps1` para refrescar cache do Pipefy periodicamente (estava congelado em 27/05/2026).
- **Pendência em aberto (da 12ª ed.):** comunicar Caio sobre cards parados nas colunas "dias desocupado" (23/24 fora do balde correto).

---
*Gerado automaticamente pela routine Claude Code em 19/06/2026 às 00:00 UTC*
