# Validação Semanal — Painel TRK
**Data:** 22/05/2026
**Status:** ✅ OK

## Resumo
Painel atualizado há 1 dia (21/05/2026). Todos os 5 colaboradores presentes com notas válidas entre 0 e 10. Nenhum campo crítico ausente.

## Última atualização do painel
- **Data:** 2026-05-21T15:57:48Z
- **Dias desde última atualização:** 1

## Notas atuais
| Pessoa | Nota | Bônus |
|---|---|---|
| Caio | 5,53 | N=3 |
| Vivianne | 5,25 | N=62 |
| Natália | 4,75 | N=5 |
| Gardênia | 4,39 | N=4 |
| Marinho | 3,82 | — |

## Delta vs 11ª Edição (pós-correção 19/05/2026)
| Pessoa | Nota 11ª (corr.) | Nota atual | Δ |
|---|---:|---:|---:|
| Caio | 5,38 | 5,53 | **+0,15** |
| Vivianne | 5,24 | 5,25 | **+0,01** |
| Natália | 4,75 | 4,75 | 0,00 |
| Gardênia | 4,44 | 4,39 | **−0,05** |
| Marinho | 3,82 | 3,82 | 0,00 |

## Validações
- [x] Arquivo atualizado nos últimos 7 dias
- [x] Todos os 5 colaboradores presentes
- [x] Notas dentro da faixa 0-10
- [x] Sem campos críticos vazios

## Observações
- **Marinho** · `bonus_proc = null` esperado — bônus N=0, sem processo de bônus aplicado nesta edição. 12 dos 13 processos sem score (apenas **Vistorias** tem dado), compatível com cargo de Vistoriador.
- **Vivianne** · bônus N=62 vs N=61 na 11ª ed. — drift natural de +1 caso de inadimplência proativa; dentro do esperado.
- **Caio** · alta de +0,15 vs 11ª ed. — aumento em Com. Locação; consistente com nova janela de dados do pipeline.
- **Gardênia** · queda de −0,05 vs 11ª ed. — variação mínima, sem alerta.
- Sem OFFs nem campos obrigatórios nulos fora do padrão.

---
*Gerado automaticamente pela routine Claude Code em 22/05/2026*
