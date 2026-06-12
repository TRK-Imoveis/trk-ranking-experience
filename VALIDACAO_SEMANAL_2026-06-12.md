# Validação Semanal — Painel TRK
**Data:** 12/06/2026
**Status:** ⚠️ Atenção

## Resumo
Arquivo atual.json gerado hoje (0 dias de defasagem) com todos os 5 colaboradores presentes e notas válidas. Atenção: BackOffice zerado para Natália e Gardênia; Marinho em queda de -0,36 vs. 11ª edição; Caio assume 2º lugar (superado por Vivianne).

## Última atualização do painel
- **Data:** 12/06/2026 às 19:43 UTC (`_meta.geradoEm`)
- **Dias desde última atualização:** 0 (gerado hoje)

## Notas atuais
| Pessoa | Nota | Bônus | Δ vs 11ª Ed |
|---|---|---|---|
| Vivianne | 5,39 | N=61 (Inadimplência) | -0,03 |
| Caio | 5,23 | N=3 (Com. Locação) | -0,20 |
| Natália | 4,81 | N=5 (Cont. ADM) | -0,12 |
| Gardênia | 4,57 | N=4 (Cont. ADM) | +0,04 |
| Marinho | 3,58 | — | -0,36 |

> Referência 11ª Edição (snapshot 27/05/2026 pós-correções): Caio 5,43 · Vivianne 5,42 · Natália 4,93 · Gardênia 4,53 · Marinho 3,94

## Validações
- [x] Arquivo atualizado nos últimos 7 dias ✅ (0 dias — gerado hoje)
- [x] Todos os 5 colaboradores presentes ✅ (Caio, Vivianne, Natália, Gardênia, Marinho)
- [x] Notas dentro da faixa 0-10 ✅ (min 3,58 · max 5,39)
- [x] Sem campos críticos vazios ✅ (`bonus_proc=null` para Marinho é esperado com bônus=0; scores null refletem áreas fora da atuação de cada colaborador)

## Observações
1. **Mudança de liderança:** Vivianne (5,39) ultrapassa Caio (5,23) e assume o 1º lugar nesta edição.
2. **BackOffice = 0,0** para Natália (0/2 pendências) e Gardênia (0/5 pendências) — ambas zeradas no indicador "Pendência <24h". Padrão já presente na 11ª edição (0,00 para Gardênia); verificar se há piora operacional.
3. **Marinho** queda expressiva: -0,36 vs. 11ª (3,58 vs. 3,94). Contestações respondidas <24h: apenas 1/10 (10,0%) — indicador crítico muito baixo.
4. **Caio:** queda de -0,20; "Comercial — Card na coluna correta" com 0/27 (0,0%) é o ponto de maior atenção desta edição.
5. **Rescisão ADM** (Natália e Gardênia): `Distrato assinado` com 0% (0/2 e 0/5 respectivamente) — campo crítico sem melhora.
6. Campos `DIRF/DARF` com meta "antes de 29/05/2026" já vencida — considerar atualizar meta para próxima edição.

---
*Gerado automaticamente pela routine Claude Code em 12/06/2026 19:43 UTC*
