# RELATÓRIO FINAL — 12ª EDIÇÃO DO RANKING TRK EXPERIENCE

**Data de fechamento:** 18/06/2026
**Pipeline:** 100% Pipefy + Octadesk + Imobiliar (local)
**Snapshot:** `docs/dados/atual.json` (ref 2026-06-18)

---

## NOTAS FINAIS

| Pos | Nome | Nota 12ª | Nota 11ª | Δ | Bônus aplicado |
|----:|------|---------:|---------:|---:|----------------|
| 1 | Vivianne Fontes ⬆ | **6,25** | 5,01 | +1,24 | N=66 em Inadimplência |
| 2 | Natália Teixeira ⬆ | **4,92** | 4,02 | +0,90 | N=6 em Cont. ADM |
| 3 | Gardênia ⬇ | **4,64** | 4,10 | +0,54 | N=4 em Cont. ADM |
| 4 | Caio Rodrigues Lima ⬇ | **4,62** | 5,34 | −0,72 | N=4 em Com. Locação |
| 5 | Albérico Marinho | **3,90** | 3,91 | −0,01 | — |

**Mudança de liderança:** Vivianne assume o 1º lugar; Caio cai de 1º para 4º. As duas
maiores variações (Vivianne +1,24 e Caio −0,72) têm causa identificada e documentada
abaixo — não há OFF de modelo.

---

## ⚠️ DOIS ACHADOS ESTRUTURAIS DESTA EDIÇÃO

### A. Cache do Pipefy estava congelado em 27/05/2026
O `atualizar_painel.ps1` rodava `python pipeline/run.py` **sem `--no-cache`**, então desde
27/05 os commits diários "Atualizar dados" só refrescavam Octadesk/CSV (baixados à mão) —
**todos os indicadores do Pipefy ficaram parados por 3 semanas**. A 12ª foi fechada após
re-extração completa (`--no-cache`), trazendo ~1 mês de movimentação real. Isso explica
parte das variações grandes. **Pendência aberta:** corrigir o `.ps1` para refrescar o
Pipefy periodicamente (ver CHECKLIST).

### B. Bug de horas úteis em cards reabertos — CORRIGIDO (era "latente" desde a 11ª)
Não era latente: **73/265 cards reabertos na Confecção** e **59/253 na Conferência**. Ver
seção "Mudanças de metodologia".

---

## MUDANÇAS DE METODOLOGIA NA 12ª ED

### 1. Correção de horas ÚTEIS em fases reabertas (Confecção / Conferência)
**Problema:** o indicador usava `horas_uteis(firstTimeIn, lastTimeOut)`. Quando um card
entra, sai e volta à mesma fase, essa janela engloba o tempo em que o card esteve em
OUTRAS fases — superestimando grosseiramente (ex.: IM1471 — janela de 173h vs 1,7h reais
na fase; IM1827 — 58h vs 0,17h).

**Solução:** novo helper `calculate.horas_uteis_fase(first_in, last_in, last_out, dur_dias)`,
usado também nos drilldowns (`imoveis_builder`), eliminando a duplicação (Armadilha 1). Como
o Pipefy reporta o histórico AGREGADO por fase (não cada passagem), a reconstrução é:
- **1 visita** (`last_in == first_in`): janela exata — idêntico ao cálculo antigo.
- **2 visitas:** última visita `[last_in, last_out]` exata + restante do `duration`
  ancorado em `first_in` — exato.
- **3+ visitas:** bloco anterior aproximado como contíguo a partir de `first_in`
  (aproximação documentada; usa só o `duration` real, nunca a janela inteira).

**Propriedade de segurança:** o tempo reconstruído é sempre ⊆ janela `[first_in, last_out]`,
logo `horas_uteis_fase ≤ horas_uteis(in,out)`. A correção **só remove falsos-negativos,
nunca cria falsos-positivos**.

**Impacto:** afeta materialmente apenas a Vivianne.
- Vivianne · Cont. ADM · Confecção <2h: **11/27 → 20/29** (sobre dados frescos).
- Assessoras · Conferência ≤2h: zero flips (os cards delas passam de 2h mesmo com o
  cálculo correto — Natália 2/11, Gardênia 1/15).

### 2. Bônus Caio · Override manual validado — IM143
IM143 (CLN 211 Bloco D Sala 101) foi alugado **antes** de publicação real (card de locação
VK5464, 1º Boleto 16/06/2026). A regra automática o excluía porque um card do Caio
(07/05/2026) tinha "Data publicação Anúncio"=08/05/2026 preenchido. A gestora confirmou
(18/06/2026) que **não houve publicação real** — o imóvel foi alugado quando estava em
Agendamento de Fotos/Placas. Incluído via `config/bonus_caio.json.edicao_12_override_incluir`.
**Impacto:** Caio N=3 → N=4.

---

## DETALHAMENTO POR COLABORADOR

### 1. Vivianne Fontes — 6,25 (BackOffice · Inadimplência) ⬆

| Processo | Indicadores |
|---|---|
| Cont. ADM | Confecção **20/29** (+correção horas úteis) |
| Rescisão ADM | Encerramento 3/6 |
| Cont. Locação | NIDO→Concl. 13/28 · Confecção 35/40 |
| Rescisão Loc. | Taxas Prop 17/26 · Taxas Final 18/23 |
| Renovação | Confecção 15/24 · Finalização 7/20 |
| Inadimplência | Cobrança 257/291 · CredPago 15/15 · Negativação 1/17 · **bônus N=66** |
| BackOffice | Concluído 111/150 · Troca Tit 11/31 |
| Ticket | SLA 136/337 |

Drivers do +1,24: correção de horas úteis na Confecção (peso 10 no Cont. ADM) + bônus
Inadimplência 61→66 + drift natural de 1 mês de dados frescos.

### 2. Natália Teixeira — 4,92 (Assessora) ⬆

Conferência 2/11 · Rescisão ADM Repasse **1/2** (era 0) · Distrato 0/2 · Rescisão Loc.
8/12 e 3/7 · Reparos 27/34 e 10/36 · Renovação 2/13 e 3/13 · BackOffice Pendência **1/5**
(era 0) · DIRF **20/31** (era 14/31) · WhatsApp 2128/2473 + 196/203 · Tickets 228/359 + 24/29
· **bônus N=6** (IM1831, 1827, 1841, 1842, 1843, 1847).

Driver do +0,90: processos de N pequeno (Rescisão ADM, BackOffice) saindo de zero +
DIRF/DARF concluído antes do cutoff 29/05 + crescimento natural Octadesk.

### 3. Gardênia — 4,64 (Assessora) ⬇

Conferência 1/15 · Rescisão ADM 2/4 e 0/6 · Rescisão Loc. 8/14 e **10/10** · Reparos 45/69
e 11/42 · Renovação 6/16 e 3/7 · BackOffice 0/12 · DIRF 3/6 · WhatsApp 2084/2574 + 240/252
· Tickets 88/232 + 6/8 · **bônus N=4** (IM1826, 1835, 1846, 1837).

Cai para 3º apenas por a Natália subir mais; em valor absoluto melhorou (+0,54).

### 4. Caio Rodrigues Lima — 4,62 (Comercial) ⬇

| Processo | Indicadores |
|---|---|
| Com. Locação | Início 10/52 · Anúncio 27/79 · **Coluna correta 1/24** · bônus N=4 |
| Cont. Locação | Ocupação 3/5 · Documentação 22/40 |
| Cont. ADM | NIDO 2/10 |
| Renovação | Avaliação >90d 12/39 |
| WhatsApp | Resposta 1408/2750 · Avals 174/189 |
| Ticket | SLA 875/2202 · Avals 21/24 |

**Driver do −0,72: "Card na coluna correta" 15/27 → 1/24** (ver achado operacional abaixo).
Bônus N=4 (IM39, IM123, IM135 continuação + IM143 override).

### 5. Albérico Marinho — 3,90 (Vistoriador)

Laudos ≤24h 36/53 · Contestações <24h 1/10. Estável vs 11ª.

---

## ACHADO OPERACIONAL — CAIO · CARDS PARADOS NAS COLUNAS "DIAS DESOCUPADO"

O indicador "Card na coluna correta" compara a fase atual do card com a fase esperada dado
quantos dias desde a publicação (15/30/60/90/180 dias desocupado). É medido na data do
fechamento.

**Diagnóstico:** dos 24 cards no denominador, **18 estão em "60 Dias desocupado" mas já
deviam estar em "90"** (publicados há 97–140 dias) e 3 estão em "15" devendo estar em "30".
O padrão é sistemático: os cards estão **exatamente um balde atrasados** — não foram
avançados conforme os imóveis seguiram desocupados nos 35 dias desde a 11ª.

**Classificação:** drift operacional REAL, não bug (a função está correta). Espelha a regra
do Marinho na 11ª (cards parados penalizam — métrica educativa).

**Ação:** comunicar ao Caio a necessidade de avançar os cards pelas colunas "dias
desocupado" (pendência registrada no CHECKLIST). A reavaliação de uma eventual tolerância
de 1 balde fica como discussão futura, se desejado.

---

## BÔNUS — RESUMO

| Bônus | N (12ª) | N (11ª) | Nota |
|---|---:|---:|---|
| Caio · Comercial | 4 | 3 | Continuação IM39, IM123, IM135 + override IM143 |
| Vivianne · Inadimplência | 66 | 61 | Regra estrita R1+R2+R3 mantida; +5 drift natural |
| Natália · Vistoria entrada | 6 | 5 | +IM1847 |
| Gardênia · Vistoria entrada | 4 | 5 | −1 (janela rolando) |

**Candidatos Caio descartados (15):** os 12 já descartados na 11ª permanecem; 3 novos
descartados — IM1586 (anunciado, card da Natália), IM1843 e IM1848 (sem card no Comercial,
entrada direta em ADM). Detalhe em `config/bonus_caio.json.edicao_12_descartados`.

---

## OFFs REAIS

**0** OFFs de modelo. Todas as variações têm causa documentada: correção intencional
(horas úteis), drift operacional real (coluna correta Caio), volatilidade de N pequeno
(assessoras), ou drift natural de janela rolando + 1 mês de dados frescos.

---

## STATUS

- ✅ Bug de horas úteis em cards reabertos corrigido (`calculate.horas_uteis_fase`)
- ✅ Re-extração completa do Pipefy (cache estava congelado em 27/05)
- ✅ Bônus validados pela gestora (incl. override IM143)
- ✅ Análise de drift sem OFFs de modelo
- ✅ Baseline atualizada (BASELINE_9 → notas da 11ª) · chaves `edicao_12`
- ✅ 12ª Edição fechada e auditada em 18/06/2026

### Pendências abertas (ver CHECKLIST_PENDENTE.md)
- 🔴 Corrigir `atualizar_painel.ps1` para refrescar o cache do Pipefy.
- 🟡 Comunicar Caio sobre cards parados nas colunas "dias desocupado".
