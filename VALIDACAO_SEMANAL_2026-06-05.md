# Validação Semanal — Painel TRK
**Data:** 05/06/2026
**Status:** ✅ OK

## Resumo
Painel atualizado hoje (0 dias de defasagem). Todos os 5 colaboradores presentes com notas válidas entre 0 e 10. Destaque para inversão de liderança: Vivianne (5,35) superou Caio (5,34) pela primeira vez. Alertas de desempenho em BackOffice e Rescisão ADM para Natália e Gardênia.

## Última atualização do painel
- **Data:** 2026-06-05T12:51:24Z (`_meta.geradoEm`)
- **Dias desde última atualização:** 0

## Notas atuais
| Pos | Pessoa | Nota | Bônus | Δ vs 11ª Ed |
|---|---|---|---|---|
| 1 | Vivianne | 5,35 | N=61 (Inadimplência) | -0,07 ⬆ 1ª |
| 2 | Caio | 5,34 | N=3 (Com. Locação) | -0,09 ⬇ 2ª |
| 3 | Natália | 4,79 | N=5 (Cont. ADM) | -0,14 |
| 4 | Gardênia | 4,57 | N=4 (Cont. ADM) | +0,04 |
| 5 | Marinho | 4,06 | — | +0,12 |

> Referência da 11ª Ed: snapshot final de 27/05/2026 (pós-correção tolerância de horas).

## Validações
- [x] Arquivo atualizado nos últimos 7 dias — gerado **hoje** (0 dias)
- [x] Todos os 5 colaboradores presentes — Vivianne, Caio, Natália, Gardênia, Marinho ✓
- [x] Notas dentro da faixa 0-10 — mín. 4,06 · máx. 5,35 ✓
- [x] Sem campos críticos vazios — `bonus_proc: null` para Marinho é esperado (sem bônus)

## Delta de Notas vs. 11ª Edição

| Pessoa | 11ª Ed (27/05) | Atual (05/06) | Δ |
|---|---:|---:|---:|
| Vivianne | 5,42 | **5,35** | -0,07 |
| Caio | 5,43 | **5,34** | -0,09 |
| Natália | 4,93 | **4,79** | -0,14 |
| Gardênia | 4,53 | **4,57** | +0,04 |
| Marinho | 3,94 | **4,06** | +0,12 |

## Observações

### ⚠️ Alertas de desempenho (scores zerados)
- **Natália — BackOffice:** 0,0 pts (0/2 pendências resolvidas em <24h). Score zerado.
- **Gardênia — BackOffice:** 0,0 pts (0/5 pendências resolvidas em <24h). Score zerado.
- **Natália — Rescisão ADM · Distrato assinado:** 0,0% (0/2 casos preenchidos).
- **Gardênia — Rescisão ADM · Distrato assinado:** 0,0% (0/5 casos preenchidos).
- **Gardênia — Cont. ADM · Conferência ≤2h:** 0,0% (0/13 contratos no prazo).

### ⚠️ Marinho — desempenho em Contestações
- Contestações respondidas <24h: **18,8%** (3/16) — ponto de atenção recorrente.
- Laudos ≤24h: 62,5% (30/48) — dentro do histórico.

### ℹ️ Mudança de liderança
- Vivianne subiu para **1ª posição** (5,35 vs 5,34 de Caio). Margem de 0,01 pt.
- Todos os colaboradores registraram queda ou estabilidade de nota vs. 11ª Ed, exceto Gardênia (+0,04) e Marinho (+0,12).

### ℹ️ Integridade dos dados
- `octadesk_disponivel: true` e `imobiliar_disponivel: true` — ambas as fontes externas disponíveis no momento da geração.
- Scores `null` em processos não aplicáveis a cada colaborador são esperados pelo modelo.

---
*Gerado automaticamente pela routine Claude Code em 05/06/2026 às 12:51 UTC*
