# Validação Semanal — Painel TRK
**Data:** 26/06/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia (2026-06-25), todos os 5 colaboradores presentes com notas válidas. Notas estáveis vs 12ª edição; Marinho recupera +0,13 e Caio/Gardênia recuam levemente.

## Última atualização do painel
- **Data:** 2026-06-25T13:58:08Z
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus | Δ vs 12ª ed |
|---|---|---|---|
| Vivianne | 6,27 | N=66 | +0,02 |
| Natália | 4,90 | N=6 | −0,02 |
| Caio | 4,51 | N=4 | −0,11 |
| Gardênia | 4,51 | N=3 | −0,13 |
| Marinho | 4,03 | — | +0,13 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias (1 dia atrás)
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios (bonus_proc=null para Marinho é esperado com bônus N=0)

## Delta vs edições anteriores

| Pessoa | 11ª | 12ª | Atual | Δ 12ª→atual |
|---|---:|---:|---:|---:|
| Vivianne | 5,01 | 6,25 | 6,27 | +0,02 |
| Natália | 4,92 | 4,92 | 4,90 | −0,02 |
| Caio | 5,34 | 4,62 | 4,51 | −0,11 |
| Gardênia | 4,10 | 4,64 | 4,51 | −0,13 |
| Marinho | 3,91 | 3,90 | 4,03 | +0,13 |

## Observações
- ⚠️ **Gardênia · BackOffice Pendência <24h: 0/11 (0,0%)** — zero execuções dentro do prazo, mesma situação crônica das edições anteriores. Requer atenção operacional.
- ⚠️ **Caio · Coluna correta: 1/24 (4,2%)** — indicador ainda crítico, pendência já identificada na 12ª edição (comunicar ao Caio para avançar cards pelos baldes de "dias desocupado").
- ℹ️ Vivianne lidera com folga (6,27); Caio e Gardênia empatados em 4,51; Marinho recupera levemente.
- ℹ️ Pendência da 12ª ainda aberta: corrigir `atualizar_painel.ps1` para refrescar cache Pipefy periodicamente.

---
*Gerado automaticamente pela routine Claude Code em 2026-06-26*
