# Validação Semanal — Painel TRK
**Data:** 18/09/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 4 dias (dentro do prazo de 7 dias), todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 14/09/2026 (geradoEm: 2026-09-14T20:03:50.428126Z, ref: 2026-09-14T19:41:35.569738+00:00)
- **Dias desde última atualização:** 4

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 3,77 | N=4 |
| Vivianne | 7,57 | — |
| Natália | 6,47 | N=9 |
| Gardênia | 5,23 | N=3 |
| Marinho | 6,63 | N=7 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- `octadesk_disponivel` e `imobiliar_disponivel` estão `true`, indicando integrações operacionais no momento da geração.
- Comparação com o último relatório de edição fechado (`config/relatorio_edicao_12.md`, fechamento 18/06/2026, ref 2026-06-18):

| Pessoa | Nota 12ª (fechada) | Nota atual (live) | Δ |
|---|---:|---:|---:|
| Vivianne | 6,25 | 7,57 | +1,32 |
| Natália | 4,92 | 6,47 | +1,55 |
| Gardênia | 4,64 | 5,23 | +0,59 |
| Caio | 4,62 | 3,77 | −0,85 |
| Marinho | 3,90 | 6,63 | +2,73 |

- Comparação com a última validação semanal registrada (`VALIDACAO_SEMANAL_2026-07-31.md`, ref 2026-07-31):

| Pessoa | Nota 31/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,18 | 7,57 | +1,39 |
| Natália | 5,26 | 6,47 | +1,21 |
| Gardênia | 4,84 | 5,23 | +0,39 |
| Caio | 4,65 | 3,77 | −0,88 |
| Marinho | 4,19 | 6,63 | +2,44 |

  Não há relatório de edição mais recente que o da 12ª (`config/relatorio_edicao_13.md` ainda não existe); `atual.json` reflete dados "ao vivo" de uma edição em andamento, então as comparações acima são apenas indicativas, não uma variação oficial de edição fechada.
- **Alerta de processo:** o último arquivo `VALIDACAO_SEMANAL_*.md` antes deste é de 31/07/2026 — houve uma lacuna de cerca de 7 semanas sem geração deste relatório (rotina aparentemente não executou entre agosto e meados de setembro). Isso não afeta a saúde dos dados no `atual.json` (que segue sendo atualizado normalmente), mas vale investigar por que a rotina semanal ficou pausada.
- Maior variação da semana/período: Marinho (+2,44 vs. última validação, +2,73 vs. 12ª edição fechada), que passou a ter bônus (N=7 em Vistorias) — anteriormente aparecia sem bônus. Caio foi o único com queda (−0,88 vs. última validação), mantendo-se na última posição do ranking atual.
- Os valores de `scores` por categoria contêm vários `null`, o que é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score relevante em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.

---
*Gerado automaticamente pela routine Claude Code em 18/09/2026 20:07 UTC*
