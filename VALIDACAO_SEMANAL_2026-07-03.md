# Validação Semanal — Painel TRK
**Data:** 03/07/2026
**Status:** ✅ OK

## Resumo
Painel atualizado no mesmo dia da validação, os 5 colaboradores estão presentes com notas dentro da faixa esperada (0-10) e sem variações anômalas em relação ao fechamento da 12ª Edição (18/06/2026).

## Última atualização do painel
- **Data:** 03/07/2026 14:01 UTC (`_meta.geradoEm`); ref dos dados: 03/07/2026 13:41 UTC
- **Dias desde última atualização:** 0

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,25 | N=4 |
| Vivianne | 6,33 | N=66 |
| Natália | 4,90 | N=8 |
| Gardênia | 4,47 | N=4 |
| Marinho | 3,81 | — |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- Delta vs. fechamento da 12ª Edição (`config/relatorio_edicao_12.md`, 18/06/2026): Vivianne 6,25→6,33 (+0,08), Natália 4,92→4,90 (−0,02), Gardênia 4,64→4,47 (−0,17), Caio 4,62→4,25 (−0,37), Marinho 3,90→3,81 (−0,09). Todas as variações são pequenas e compatíveis com drift natural de dados (janela rolando); nenhuma indica anomalia ou possível bug.
- Campos `scores` com valor `null` por pessoa (ex.: processos não aplicáveis ao cargo, como "Reparos" para Vivianne ou "Vistorias" para as assessoras) são esperados pela estrutura do painel e não representam dados faltantes.
- `bonus_proc: null` para Marinho é esperado, pois seu bônus é 0 (não há processo de bônus aplicável ao cargo de Vistoriador).
- Ranking segue igual ao da 12ª Edição: 1º Vivianne, 2º Natália, 3º Gardênia, 4º Caio, 5º Marinho.

---
*Gerado automaticamente pela routine Claude Code em 03/07/2026 14:30 UTC*
