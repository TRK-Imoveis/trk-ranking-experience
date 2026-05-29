# Validação Semanal — Painel TRK
**Data:** 29/05/2026
**Status:** ✅ OK

## Resumo
Todos os 5 colaboradores estão presentes, notas dentro da faixa 0–10 e arquivo atualizado há 2 dias. Os dados correspondem ao estado final corrigido da 11ª edição (correções pós-fechamento de 19/05 e 27/05/2026 já aplicadas).

## Última atualização do painel
- **Data:** 2026-05-27T18:59:14Z
- **Dias desde última atualização:** 2

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 5,43 | N=3 |
| Vivianne | 5,42 | N=61 |
| Natália | 4,93 | N=5 |
| Gardênia | 4,53 | N=4 |
| Marinho | 3,94 | — |

## Delta vs 11ª Edição (14/05/2026)
| Pessoa | Nota 11ª | Nota atual | Δ | Observação |
|---|---:|---:|---:|---|
| Caio | 5,34 | 5,43 | +0,09 | Correção tolerância 27/05 |
| Vivianne | 5,01 | 5,42 | +0,41 | Correção Resc. ADM 19/05 + tolerância 27/05 |
| Natália | 4,02 | 4,93 | +0,91 | Correção posicionamento 11ª + tolerância 27/05 |
| Gardênia | 4,10 | 4,53 | +0,43 | Correção posicionamento 11ª + tolerância 27/05 |
| Marinho | 3,91 | 3,94 | +0,03 | Correção tolerância 27/05 |

> Os deltas são integralmente explicados pelas correções pós-fechamento documentadas em `config/relatorio_edicao_11.md` (seções 19/05 e 27/05/2026). Não há variação de performance nova neste ciclo.

## Validações
- [x] Arquivo atualizado nos últimos 7 dias (2 dias)
- [x] Todos os 5 colaboradores presentes (Caio, Vivianne, Natália, Gardênia, Marinho)
- [x] Notas dentro da faixa 0–10 (mín: 3,94 · máx: 5,43)
- [x] Sem campos críticos vazios (`nota` preenchida para todos; `bonus_proc` null apenas para Marinho com bônus=0, esperado)

## Observações
- **BackOffice = 0,0** para Natália (0/2 pendências <24h) e Gardênia (0/5 pendências <24h): trata-se de performance operacional real (zero casos no prazo), não dado faltante.
- **Marinho** avaliado em apenas 2 indicadores (Laudos ≤24h e Contestações <24h) — volume baixo de contestações respondidas no prazo (3/17 = 17,6%) continua como ponto de atenção.
- **DIRF/DARF em andamento:** Natália 16/31 (51,6%) e Gardênia 3/6 (50,0%) — prazo final 29/05/2026, mesmo dia desta validação.
- Não há dados de nova edição (12ª); o `atual.json` reflete o snapshot final da 11ª edição corrigida.

---
*Gerado automaticamente pela routine Claude Code em 29/05/2026 às 00:00 UTC*
