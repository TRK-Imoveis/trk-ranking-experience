# Validação Semanal — Painel TRK
**Data:** 25/09/2026
**Status:** ⚠️ Atenção

## Resumo
Painel atualizado há 2 dias, todos os 5 colaboradores originais presentes com notas válidas (0-10) e sem campos críticos vazios. Sinalizado para atenção: variações grandes de nota desde a última checagem, uma 6ª pessoa (Tauise) agora presente no painel, e um hiato de quase 2 meses desde a última validação semanal registrada.

## Última atualização do painel
- **Data:** 23/09/2026 (geradoEm: 2026-09-23T12:47:47.272618Z, ref: 2026-09-23T12:20:59.793926+00:00)
- **Dias desde última atualização:** 2

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 3,90 | N=4 |
| Vivianne | 7,85 | — |
| Natália | 6,45 | N=9 |
| Gardênia | 5,69 | N=4 |
| Marinho | 6,66 | N=8 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- **6ª pessoa no painel:** `PESSOAS` agora inclui **Tauise Oliveira** (Assessora, nota 3,59, sem bônus), que não constava na lista original de 5 colaboradores nem na validação anterior (31/07/2026). Não é um erro de dados — parece uma inclusão legítima na equipe — mas está fora do escopo dos 5 nomes que esta rotina foi configurada para checar; vale atualizar a lista de referência.
- **Hiato na cadência semanal:** a última validação registrada no repositório é `VALIDACAO_SEMANAL_2026-07-31.md` (ref. 31/07/2026) — quase 2 meses atrás, não 1 semana. A rotina não rodou (ou não commitou) nas semanas intermediárias.
- **`octadesk_disponivel`** e **`imobiliar_disponivel`** estão `true`; `etl_ultima_carga` está `null` em `_meta`, o que é esperado quando `fonte: "api"` (dados ao vivo, não via ETL) — não é um campo crítico vazio.
- Comparação com o último relatório de edição fechado (`config/relatorio_edicao_12.md`, fechamento 18/06/2026, ref 2026-06-18):

| Pessoa | Nota 12ª (fechada) | Nota atual (live) | Δ |
|---|---:|---:|---:|
| Vivianne | 6,25 | 7,85 | +1,60 |
| Natália | 4,92 | 6,45 | +1,53 |
| Gardênia | 4,64 | 5,69 | +1,05 |
| Caio | 4,62 | 3,90 | −0,72 |
| Marinho | 3,90 | 6,66 | +2,76 |

  Não há relatório de edição mais recente que a 12ª — defasagem de mais de 3 meses sem fechamento formal. Recomenda-se avaliar o fechamento de uma nova edição.

- Comparação com a última validação semanal (`VALIDACAO_SEMANAL_2026-07-31.md`, ref 31/07):

| Pessoa | Nota 31/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,18 | 7,85 | +1,67 |
| Natália | 5,26 | 6,45 | +1,19 |
| Gardênia | 4,84 | 5,69 | +0,85 |
| Caio | 4,65 | 3,90 | −0,75 |
| Marinho | 4,19 | 6,66 | +2,47 |

  Todas as variações são grandes em magnitude, consistentes com o hiato de quase 2 meses entre checagens (mais tempo acumulando movimentação). Marinho e Vivianne subiram significativamente; Caio segue em tendência de queda (já vinha caindo desde a 12ª edição). Nenhuma nota saiu da faixa válida, mas a amplitude das variações justifica uma revisão humana antes de considerar o painel "rotineiro" novamente.
- Os valores de `scores` por categoria contêm vários `null`, o que é esperado (refletem categorias que não se aplicam ao cargo de cada pessoa). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo para os 6 colaboradores presentes.

---
*Gerado automaticamente pela routine Claude Code em 25/09/2026*
