# Validação Semanal — Painel TRK
**Data:** 17/07/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia, todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 16/07/2026 (geradoEm: 2026-07-16T14:54:01Z, ref: 2026-07-16T14:34:18Z)
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,79 | N=4 |
| Vivianne | 6,39 | N=66 |
| Natália | 5,07 | N=7 |
| Gardênia | 4,78 | N=4 |
| Marinho | 3,42 | — |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- `octadesk_disponivel` e `imobiliar_disponivel` estão `true`, indicando integrações operacionais no momento da geração.
- Comparação com a última validação semanal (`VALIDACAO_SEMANAL_2026-07-10.md`, ref 09/07/2026):

| Pessoa | Nota 10/07 | Nota atual (live) | Δ |
|---|---:|---:|---:|
| Caio | 4,39 | 4,79 | +0,40 |
| Vivianne | 6,40 | 6,39 | −0,01 |
| Natália | 5,14 | 5,07 | −0,07 |
| Gardênia | 4,54 | 4,78 | +0,24 |
| Marinho | 3,43 | 3,42 | −0,01 |

  Variações modestas, sem outliers ou saltos abruptos.
- Comparação com o último relatório de edição fechada (`config/relatorio_edicao_12.md`, fechamento 18/06/2026): a 13ª edição segue em andamento (dados "ao vivo", ainda não fechada/reportada); a tabela acima é apenas indicativa, não uma variação oficial de edição fechada.
- Os valores de `scores` por categoria contêm vários `null`, mas isso é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.

---
*Gerado automaticamente pela routine Claude Code em 17/07/2026 (ref. execução da rotina)*
