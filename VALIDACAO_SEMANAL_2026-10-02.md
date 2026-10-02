# Validação Semanal — Painel TRK
**Data:** 02/10/2026
**Status:** ⚠️ Atenção

## Resumo
Painel atualizado há 3 dias, com os 5 colaboradores presentes e notas válidas (0-10). Atenção: Vivianne está sem bônus (N=0, antes N=49), Caio caiu para 3,88 (−0,77 vs 31/07) e há uma 6ª pessoa (Tauise) em PESSOAS.

## Última atualização do painel
- **Data:** 29/09/2026 (geradoEm: 2026-09-29T11:37:09Z, ref: 2026-09-29T11:30:47Z)
- **Dias desde última atualização:** 3

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 3,88 | N=4 (Com. Locação) |
| Vivianne | 7,92 | N=0 |
| Natália | 6,47 | N=9 (Cont. ADM 8 + Renovação 1) |
| Gardênia | 5,77 | N=4 (Cont. ADM) |
| Marinho | 6,60 | N=8 (Vistorias) |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios (ver observações sobre bônus)

## Observações
- Delta vs. última validação (31/07/2026):

| Pessoa | Nota 31/07 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 6,18 | 7,92 | +1,74 |
| Natália | 5,26 | 6,47 | +1,21 |
| Gardênia | 4,84 | 5,77 | +0,93 |
| Marinho | 4,19 | 6,60 | +2,41 |
| Caio | 4,65 | 3,88 | −0,77 |

- Último relatório de edição fechada disponível: `config/relatorio_edicao_12.md` (18/06/2026): Vivianne 6,25, Natália 4,92, Gardênia 4,64, Caio 4,62, Marinho 3,90. Não há relatório da 13ª edição; os valores atuais são "ao vivo".
- **Vivianne com bônus N=0** (`bonus_proc` null) — nas edições anteriores tinha N=49–66 em Inadimplência. Verificar se é mudança intencional de regra/edição ou falha de configuração (`config/bonus_vivianne.json`).
- **Caio** é o único com queda (−0,77) e fica em último lugar, com apenas 11 indicadores e 60 pts.
- Marinho passou a ter bônus (N=8 em Vistorias), antes sem bônus. Natália subiu de N=6 para N=9.
- `PESSOAS` contém uma 6ª pessoa não prevista: Tauise Oliveira (nota 4,67, sem bônus, `bonus_proc` null). Confirmar se é esperado.
- `etl_ultima_carga` está null; `octadesk_disponivel` e `imobiliar_disponivel` são `true`. Os `null` em `scores` são categorias não aplicáveis ao cargo.
- Existem lacunas na série de validações (última anterior: 31/07); o pipeline pode ter ficado sem execução em algumas semanas.

---
*Gerado automaticamente pela routine Claude Code em 02/10/2026 20:02 UTC*
