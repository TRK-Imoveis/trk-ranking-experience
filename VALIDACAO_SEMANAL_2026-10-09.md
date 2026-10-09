# Validação Semanal — Painel TRK
**Data:** 09/10/2026
**Status:** ⚠️ Atenção

## Resumo
Painel atualizado há 1 dia, com os 5 colaboradores presentes e notas válidas (0-10). Atenção: Vivianne segue sem bônus (N=0) e há uma 6ª pessoa (Tauise) em PESSOAS.

## Última atualização do painel
- **Data:** 08/10/2026 (geradoEm: 2026-10-08T13:01:29Z, ref: 2026-10-08T12:54:25Z, fonte: api)
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 3,81 | N=3 (Com. Locação) |
| Vivianne | 7,94 | N=0 |
| Natália | 6,29 | N=8 (Cont. ADM 7 + Renovação 1) |
| Gardênia | 6,06 | N=4 (Cont. ADM) |
| Marinho | 6,56 | N=8 (Vistorias) |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios (ver observações sobre bônus)

## Observações
- Delta vs. última validação (02/10/2026):

| Pessoa | Nota 02/10 | Nota atual | Δ |
|---|---:|---:|---:|
| Vivianne | 7,92 | 7,94 | +0,02 |
| Marinho | 6,60 | 6,56 | −0,04 |
| Natália | 6,47 | 6,29 | −0,18 |
| Gardênia | 5,77 | 6,06 | +0,29 |
| Caio | 3,88 | 3,81 | −0,07 |

- Relatórios de edição acessíveis: `config/relatorio_edicao_11.md` e `config/relatorio_edicao_12.md` (a 12ª é a mais recente; não há relatório da edição em curso, valores atuais são "ao vivo").
- **Vivianne com bônus N=0** (`bonus_proc` null), pendência já apontada em 02/10. Verificar se é intencional ou falha em `config/bonus_vivianne.json`.
- **Caio** continua em último entre os 5 (3,81), com 11 indicadores e 60 pts.
- `PESSOAS` contém uma 6ª pessoa não prevista: Tauise Oliveira (nota 4,54, sem bônus). Confirmar se é esperado.
- `etl_ultima_carga` está null; `octadesk_disponivel` e `imobiliar_disponivel` são `true`. Os `null` em `scores` são categorias não aplicáveis ao cargo.

---
*Gerado automaticamente pela routine Claude Code em 09/10/2026 20:03 UTC*
