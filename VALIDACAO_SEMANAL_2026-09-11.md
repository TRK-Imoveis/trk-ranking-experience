# Validação Semanal — Painel TRK
**Data:** 11/09/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 3 dias (dentro da janela de 7 dias), todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 08/09/2026 (geradoEm: 2026-09-08T18:34:04.157974Z, ref: 2026-09-08T18:07:47.503767+00:00)
- **Dias desde última atualização:** 3

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 3,66 | N=4 |
| Vivianne | 7,39 | N=0 |
| Natália | 6,43 | N=9 |
| Gardênia | 5,32 | N=4 |
| Marinho | 6,78 | N=7 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- `octadesk_disponivel` e `imobiliar_disponivel` estão `true`, indicando integrações operacionais no momento da geração. `etl_ultima_carga` é `null`, mas isso é o padrão observado nas edições anteriores (fonte declarada é `api`, não ETL em lote).
- Campos de detalhe (`scores` por categoria) contêm vários `null` esperados, refletindo categorias que não se aplicam ao cargo de cada pessoa (ex.: Marinho, Vistoriador, só pontua em "Vistorias"). Nenhum campo essencial (nome, cargo, nota, bônus, posição) veio vazio ou nulo.
- **Atenção — Vivianne com N=0 em Inadimplência:** desde a 12ª edição (fechada em 18/06/2026) e nas validações semanais seguintes, Vivianne sempre apresentou bônus ativo em Inadimplência (N=49 a N=66). Nesta leitura, `bonus`=0 e `bonus_proc`=`null` para ela — uma mudança notável frente ao padrão histórico que vale confirmar com a gestora (pode ser drift real da janela rolando ou possível falha de extração pontual do Octadesk/Pipefy para essa regra).
- **Marinho passou a ter bônus (N=7, Vistorias):** nas edições e validações anteriores ele aparecia sem bônus. Vale confirmar se essa é uma mudança de regra/elegibilidade recente ou um dado real de vistorias no período.
- Comparação com o último relatório de edição fechado (`config/relatorio_edicao_12.md`, fechamento 18/06/2026, ref 2026-06-18):

| Pessoa | Nota 12ª (fechada) | Nota atual (live) | Δ |
|---|---:|---:|---:|
| Vivianne | 6,25 | 7,39 | +1,14 |
| Natália | 4,92 | 6,43 | +1,51 |
| Gardênia | 4,64 | 5,32 | +0,68 |
| Caio | 4,62 | 3,66 | −0,96 |
| Marinho | 3,90 | 6,78 | +2,88 |

- Comparação com a última validação semanal disponível (`VALIDACAO_SEMANAL_2026-07-31.md`, ref 2026-07-31):

| Pessoa | Nota 31/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,18 | 7,39 | +1,21 |
| Natália | 5,26 | 6,43 | +1,17 |
| Gardênia | 4,84 | 5,32 | +0,48 |
| Caio | 4,65 | 3,66 | −0,99 |
| Marinho | 4,19 | 6,78 | +2,59 |

  Marinho e Vivianne tiveram altas expressivas desde a última validação (+2,59 e +1,21) e desde a 12ª edição fechada (+2,88 e +1,14). Caio é o único em queda, tanto vs. a 12ª edição (−0,96) quanto vs. a última validação semanal (−0,99). Não há relatório de edição fechado mais recente que a 12ª (`config/relatorio_edicao_12.md`) disponível para uma comparação oficial mais próxima — os deltas acima são indicativos, calculados sobre `atual.json` (dados "ao vivo", edição em andamento ainda não fechada).

---
*Gerado automaticamente pela routine Claude Code em 11/09/2026*
