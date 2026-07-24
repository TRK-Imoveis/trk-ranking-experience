# Validação Semanal — Painel TRK
**Data:** 24/07/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia, todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 23/07/2026 (geradoEm: 2026-07-23T15:08:00Z, ref: 2026-07-23T14:45:37Z)
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,66 | N=4 |
| Vivianne | 6,17 | N=49 |
| Natália | 5,16 | N=7 |
| Gardênia | 4,72 | N=4 |
| Marinho | 3,42 | — |

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
| Vivianne | 6,25 | 6,17 | −0,08 |
| Natália | 4,92 | 5,16 | +0,24 |
| Gardênia | 4,64 | 4,72 | +0,08 |
| Caio | 4,62 | 4,66 | +0,04 |
| Marinho | 3,90 | 3,42 | −0,48 |

- Comparação com a última validação semanal (`VALIDACAO_SEMANAL_2026-07-10.md`, ref 2026-07-09):

| Pessoa | Nota 10/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,40 | 6,17 | −0,23 |
| Natália | 5,14 | 5,16 | +0,02 |
| Gardênia | 4,54 | 4,72 | +0,18 |
| Caio | 4,39 | 4,66 | +0,27 |
| Marinho | 3,43 | 3,42 | −0,01 |

  Marinho segue com a maior queda acumulada frente à 12ª edição (−0,48), mas estável na comparação semana a semana (−0,01) — não indica uma regressão nova, apenas manutenção do patamar mais baixo desde a última edição fechada.
- Os valores de `scores` por categoria contêm vários `null`, mas isso é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.
- `atual.json` reflete dados "ao vivo" da 13ª edição em andamento (ainda não fechada/reportada); as comparações acima são apenas indicativas, não uma variação oficial de edição fechada.

---
*Gerado automaticamente pela routine Claude Code em 24/07/2026 (ref. execução da rotina)*
