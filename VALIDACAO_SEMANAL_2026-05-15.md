# Validação Semanal — Painel TRK
**Data:** 15/05/2026
**Status:** ✅ OK

## Resumo
Painel atualizado hoje (15/05/2026) com os dados finais da 11ª Edição. Todos os 5 colaboradores estão presentes, notas dentro da faixa válida e campos críticos preenchidos.

## Última atualização do painel
- **Data:** 2026-05-15T21:41:25Z
- **Dias desde última atualização:** 0

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 5,34 | N=3 |
| Vivianne | 5,01 | N=61 |
| Natália | 4,76 | N=5 |
| Gardênia | 4,38 | N=5 |
| Marinho | 3,91 | — |

## Delta vs 11ª Edição (config/relatorio_edicao_11.md)
| Pessoa | Nota atual | Nota 11ª | Δ | Nota 10ª | Δ vs 10ª |
|---|---|---|---|---|---|
| Caio | 5,34 | 5,34 | 0,00 | 5,48 | -0,14 |
| Vivianne | 5,01 | 5,01 | 0,00 | 5,22 | -0,21 |
| Natália | 4,76 | 4,76 | 0,00 | 3,98 | +0,78 |
| Gardênia | 4,38 | 4,38 | 0,00 | 3,97 | +0,41 |
| Marinho | 3,91 | 3,91 | 0,00 | 4,76 | -0,85 |

> O `atual.json` foi regenerado hoje com os dados idênticos à 11ª Edição (Δ=0,00 para todos). Os deltas relevantes são vs 10ª Edição, refletindo as mudanças de metodologia da 11ª.

## Validações
- [x] Arquivo atualizado nos últimos 7 dias ✅ (atualizado há 0 dias)
- [x] Todos os 5 colaboradores presentes ✅ (Caio, Vivianne, Natália, Gardênia, Marinho)
- [x] Notas dentro da faixa 0-10 ✅ (min=3,91 · max=5,34)
- [x] Sem campos críticos vazios ✅ (nota, bonus, inds, pts preenchidos para todos)

## Campos IMOVEIS e PROC_RICH
- **IMOVEIS:** 55 chaves preenchidas ✅ (drilldown por imóvel operacional)
- **PROC_RICH:** 13 painéis preenchidos ✅ (painéis de processo operacionais)

> Ambos os campos estavam listados como limitação conhecida no relatório da 11ª Edição, mas agora se encontram totalmente populados.

## Observações
1. **Inconsistência interna no relatorio_edicao_11.md:** a tabela inicial do relatório registra Gardênia=4,10 e Natália=4,02, enquanto a seção "STATUS FINAL" (ao fim do mesmo arquivo) registra Natália=4,76 e Gardênia=4,38. O `atual.json` está **alinhado com o STATUS FINAL** (valores autoritativos).
2. **Scores nulos por processo:** cada colaborador possui notas null nos processos que não são de sua responsabilidade — comportamento esperado e não-crítico.
   - Caio: 7 scores null (Rescisão ADM, Rescisão Loc., Reparos, Inadimplência, Vistorias, BackOffice, DIRF/DARF)
   - Vivianne: 5 scores null (Com. Locação, Reparos, Vistorias, DIRF/DARF, WhatsApp)
   - Natália: 4 scores null (Com. Locação, Cont. Locação, Inadimplência, Vistorias)
   - Gardênia: 4 scores null (Com. Locação, Cont. Locação, Inadimplência, Vistorias)
   - Marinho: 12 scores null (apenas Vistorias é seu processo)
3. **Marinho sem bônus:** `bonus_proc=null` e `bonus=0` — esperado para o cargo de Vistoriador.

---
*Gerado automaticamente pela routine Claude Code em 15/05/2026 às 21:41 UTC*
