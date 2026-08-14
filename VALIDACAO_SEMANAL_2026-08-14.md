# Validação Semanal — Painel TRK
**Data:** 14/08/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia, todos os 5 colaboradores presentes com notas válidas (0-10) e sem campos críticos vazios. Nenhum problema estrutural identificado.

## Última atualização do painel
- **Data:** 13/08/2026 (geradoEm: 2026-08-13T21:07:11.688469Z, ref: 2026-08-13T20:45:58.183657+00:00)
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 4,52 | N=4 |
| Vivianne | 6,84 | N=0 |
| Natália | 5,35 | N=5 |
| Gardênia | 4,56 | N=3 |
| Marinho | 4,14 | — |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- `octadesk_disponivel` e `imobiliar_disponivel` estão `true`, indicando integrações operacionais no momento da geração.
- Ainda não há `config/relatorio_edicao_13.md` no repositório — o `atual.json` segue refletindo dados "ao vivo" de uma edição em andamento; comparações abaixo são apenas indicativas.
- Comparação com o último relatório de edição fechado (`config/relatorio_edicao_12.md`, fechamento 18/06/2026):

| Pessoa | Nota 12ª (fechada) | Nota atual (live) | Δ |
|---|---:|---:|---:|
| Vivianne | 6,25 | 6,84 | +0,59 |
| Natália | 4,92 | 5,35 | +0,43 |
| Gardênia | 4,64 | 4,56 | −0,08 |
| Caio | 4,62 | 4,52 | −0,10 |
| Marinho | 3,90 | 4,14 | +0,24 |

- Comparação com a última validação semanal (`VALIDACAO_SEMANAL_2026-07-31.md`, ref 2026-07-31):

| Pessoa | Nota 31/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,18 | 6,84 | +0,66 |
| Natália | 5,26 | 5,35 | +0,09 |
| Gardênia | 4,84 | 4,56 | −0,28 |
| Caio | 4,65 | 4,52 | −0,13 |
| Marinho | 4,19 | 4,14 | −0,05 |

  Nenhuma variação atípica: Vivianne segue em alta (+0,66 na semana), Gardênia e Caio recuaram moderadamente sem sair da faixa de normalidade. Ponto de atenção não-crítico: o bônus de Vivianne caiu de N=49 (relatório de 31/07) para N=0 nesta leitura, com `bonus_proc` voltando a `null` — coerente com o comportamento de janela rolando já documentado para os bônus por N (ver `config/relatorio_edicao_12.md`), mas vale confirmar na próxima edição fechada que não é efeito de reprocessamento incompleto do pipeline.
- Os valores de `scores` por categoria contêm vários `null`, o que é esperado: refletem categorias que não se aplicam ao cargo/atuação de cada pessoa (ex.: Marinho, Vistoriador, só possui score em "Vistorias"). Nenhum campo essencial (nome, nota, bônus, posição) veio vazio ou nulo.

---
*Gerado automaticamente pela routine Claude Code em 14/08/2026*
