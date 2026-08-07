# Validação Semanal — Painel TRK
**Data:** 07/08/2026
**Status:** ✅ OK

## Resumo
Painel atualizado no próprio dia (0 dias de atraso), todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 07/08/2026 (geradoEm: 2026-08-07T16:35:18.376932Z, ref: 2026-08-07T16:16:59.118519+00:00)
- **Dias desde última atualização:** 0

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,62 | N=4 |
| Vivianne | 6,48 | N=49 |
| Natália | 5,71 | N=5 |
| Gardênia | 4,83 | N=4 |
| Marinho | 4,38 | — |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- `octadesk_disponivel` e `imobiliar_disponivel` estão `true`, indicando integrações operacionais no momento da geração.
- Comparação com o último relatório de edição fechado (`config/relatorio_edicao_12.md`, fechamento 18/06/2026, ref 2026-06-18) — ainda a edição fechada mais recente, a 13ª segue em andamento:

| Pessoa | Nota 12ª (fechada) | Nota atual (live) | Δ |
|---|---:|---:|---:|
| Vivianne | 6,25 | 6,48 | +0,23 |
| Natália | 4,92 | 5,71 | +0,79 |
| Gardênia | 4,64 | 4,83 | +0,19 |
| Caio | 4,62 | 4,62 | 0,00 |
| Marinho | 3,90 | 4,38 | +0,48 |

- Comparação com a última validação semanal (`VALIDACAO_SEMANAL_2026-07-31.md`, ref 2026-07-31):

| Pessoa | Nota 31/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,18 | 6,48 | +0,30 |
| Natália | 5,26 | 5,71 | +0,45 |
| Gardênia | 4,84 | 4,83 | −0,01 |
| Caio | 4,65 | 4,62 | −0,03 |
| Marinho | 4,19 | 4,38 | +0,19 |

  Natália segue com a maior alta acumulada da semana (+0,45), consolidando a recuperação já vista desde a 12ª edição fechada (+0,79 no acumulado). Variações de Gardênia e Caio são de manutenção (±0,03), sem sinal de queda relevante.
- Os valores de `scores` por categoria contêm vários `null`, mas isso é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.
- `atual.json` reflete dados "ao vivo" da 13ª edição em andamento (ainda não fechada/reportada); as comparações acima são apenas indicativas, não uma variação oficial de edição fechada.

---
*Gerado automaticamente pela routine Claude Code em 07/08/2026 (ref. execução da rotina)*
