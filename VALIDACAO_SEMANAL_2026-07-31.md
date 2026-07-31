# Validação Semanal — Painel TRK
**Data:** 31/07/2026
**Status:** ✅ OK

## Resumo
Painel atualizado no próprio dia (0 dias de atraso), todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 31/07/2026 (geradoEm: 2026-07-31T18:07:22.736701Z, ref: 2026-07-31T17:45:23.078912+00:00)
- **Dias desde última atualização:** 0

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,65 | N=4 |
| Vivianne | 6,18 | N=49 |
| Natália | 5,26 | N=6 |
| Gardênia | 4,84 | N=4 |
| Marinho | 4,19 | — |

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
| Vivianne | 6,25 | 6,18 | −0,07 |
| Natália | 4,92 | 5,26 | +0,34 |
| Gardênia | 4,64 | 4,84 | +0,20 |
| Caio | 4,62 | 4,65 | +0,03 |
| Marinho | 3,90 | 4,19 | +0,29 |

- Comparação com a última validação semanal (`VALIDACAO_SEMANAL_2026-07-24.md`, ref 2026-07-23):

| Pessoa | Nota 24/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,17 | 6,18 | +0,01 |
| Natália | 5,16 | 5,26 | +0,10 |
| Gardênia | 4,72 | 4,84 | +0,12 |
| Caio | 4,66 | 4,65 | −0,01 |
| Marinho | 3,42 | 4,19 | +0,77 |

  Marinho teve a maior alta na semana (+0,77), revertendo boa parte da queda observada nas últimas edições e voltando a ficar acima do patamar da 12ª edição fechada (+0,29). Nenhuma queda relevante nesta semana — todas as variações são de manutenção ou melhora, exceto Caio, praticamente estável (−0,01).
- Os valores de `scores` por categoria contêm vários `null`, mas isso é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.
- `atual.json` reflete dados "ao vivo" da 13ª edição em andamento (ainda não fechada/reportada); as comparações acima são apenas indicativas, não uma variação oficial de edição fechada.

---
*Gerado automaticamente pela routine Claude Code em 31/07/2026 (ref. execução da rotina)*
