# Validação Semanal — Painel TRK
**Data:** 10/07/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia, todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 09/07/2026 (geradoEm: 2026-07-09T15:36:28Z, ref: 2026-07-09T15:17:37Z)
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,39 | N=4 |
| Vivianne | 6,40 | N=66 |
| Natália | 5,14 | N=8 |
| Gardênia | 4,54 | N=4 |
| Marinho | 3,43 | — |

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
| Vivianne | 6,25 | 6,40 | +0,15 |
| Natália | 4,92 | 5,14 | +0,22 |
| Gardênia | 4,64 | 4,54 | −0,10 |
| Caio | 4,62 | 4,39 | −0,23 |
| Marinho | 3,90 | 3,43 | −0,47 |

- Os valores de `scores` por categoria contêm vários `null`, mas isso é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.
- `atual.json` reflete dados "ao vivo" da 13ª edição em andamento (ainda não fechada/reportada); a comparação acima é apenas indicativa, não uma variação oficial de edição fechada.

---
*Gerado automaticamente pela routine Claude Code em 10/07/2026 (ref. execução da rotina)*
