# RELATÓRIO FINAL — 11ª EDIÇÃO DO RANKING TRK EXPERIENCE

**Data:** 14/05/2026
**Pipeline:** 100% Pipefy + Octadesk + Imobiliar (local, sem API externa)
**Snapshot:** `painel/dados/atual.json` (16.081 bytes)

---

## NOTAS FINAIS

| Pos | Nome | Nota 11ª | Nota 10ª | Δ | Bônus aplicado |
|----:|------|---------:|---------:|---:|----------------|
| 1 | Caio Rodrigues Lima | **5,34** | 5,48 | -0,14 | N=3 em Com. Locação |
| 2 | Vivianne Fontes | **5,01** | 5,22 | -0,21 | N=61 em Inadimplência |
| 3 | Gardênia | **4,10** | 3,97 | +0,13 | N=5 em Cont. ADM |
| 4 | Natália Teixeira | **4,02** | 3,98 | +0,04 | N=5 em Cont. ADM |
| 5 | Albérico Marinho | **3,91** | 4,76 | -0,85 | — |

---

## DETALHAMENTO POR COLABORADOR

### 1. Caio Rodrigues Lima — 5,34 (Comercial)

| Processo | Nota | Indicadores |
|---|---:|---|
| Com. Locação | 5,53 | Início 7/41 · Anúncio 26/66 · Coluna 15/27 · **bônus N=3** |
| Cont. Locação | 7,29 | Ocupação 5/6 · Documentação 24/42 |
| Cont. ADM | 4,00 | NIDO 2/5 |
| Renovação | 2,89 | Avaliação >90d 11/38 |
| WhatsApp | 6,71 | Resposta ≤5min 1194/2396 · Avals 139/154 |
| Ticket | 6,19 | SLA 749/1738 · Avals 20/23 |

**Bônus N=3** (IM39, IM123, IM135 — continuação da 10ª). 15 novos candidatos validados pela gestora e **todos descartados** (11 por publicação anterior fora do recorte, 4 por entrada direta em ADM). IM1567 da 10ª saiu da janela 180d.

Drifts vs 10ª:
- Indicadores Pipefy: TODOS dentro de ±1 (drift natural).
- WhatsApp/Tickets: pequeno crescimento natural do dataset (~+2/+4 dos casos).

### 2. Vivianne Fontes — 5,01 (BackOffice · Inadimplência)

| Processo | Nota | Indicadores |
|---|---:|---|
| Cont. ADM | 4,07 | Confecção 11/27 |
| Rescisão ADM | 2,00 | Encerramento 1/5 |
| Cont. Locação | 7,90 | NIDO 11/34 · Confecção 36/42 |
| Rescisão Loc. | 5,69 | Taxas Prop 10/20 · Taxas Final 13/20 |
| Renovação | 2,73 | Confecção 11/23 · Finalização 2/18 |
| Inadimplência | 9,80 | Cobrança 240/275 · CredPago 12/14 · Negativação 1/16 · **bônus N=61** |
| BackOffice | 5,78 | Concluído 103/148 · Troca Tit 13/29 |
| Ticket | 3,69 | SLA 106/288 |

Drifts vs 10ª:
- Inadimplência ★ N: **61 vs 124** (drift -63 INTENCIONAL pela regra 11ª — ver mudanças de metodologia).
- Indicadores Pipefy: 3-4 com drift natural Δ≤+3.
- Renovação Confecção: 11/23 vs 9/21 (+2/+2 drift natural).

### 3. Gardênia — 4,10 (Assessora)

| Processo | Nota | Indicadores |
|---|---:|---|
| Cont. ADM | 2,86 | Conferência 0/12 · **bônus N=5** |
| Rescisão ADM | 0,00 | Repasse 0/2 · Distrato 0/5 |
| Rescisão Loc. | 7,67 | Boleto prop 7/12 · Boleto final 8/9 |
| Reparos | 4,87 | Orçamento 51/73 · Pós-venda 15/44 |
| Renovação | 4,00 | Contato >60d 5/15 · Assinado 4/9 |
| BackOffice | 0,00 | Pendência 0/10 |
| DIRF/DARF | 3,33 | Concluído 2/6 |
| WhatsApp | 8,71 | Resposta 1791/2190 · Avals 169/178 |
| Ticket | 4,93 | SLA 73/202 · Avals 5/8 |

**Bônus N=5** (anteriormente N=6 — fix do array vazio em "Criar Card de Vistoria Técnica": IM1845 excluído).

Drifts vs 10ª: pequenos (+1 a +5 casos) — todos compatíveis com janela rolando.

### 4. Natália Teixeira — 4,02 (Assessora)

| Processo | Nota | Indicadores |
|---|---:|---|
| Cont. ADM | 4,44 | Conferência 2/12 · **bônus N=5** |
| Rescisão ADM | 0,00 | Repasse 0/2 · Distrato 0/2 |
| Rescisão Loc. | 4,69 | Boleto prop 5/8 · Boleto final 2/5 |
| Reparos | 4,90 | Orçamento 41/52 · Pós-venda 14/53 |
| Renovação | 1,59 | Contato 3/13 · Assinado 1/9 |
| BackOffice | 0,00 | Pendência 0/2 |
| DIRF/DARF | 4,19 | Concluído 14/31 |
| WhatsApp | 9,04 | Resposta 1805/2091 · Avals 137/144 |
| Ticket | 6,98 | SLA 169/281 · Avals 19/24 |

**Bônus N=5** (IM1831, IM1827, IM1841, IM1842, IM1843).

Drifts vs 10ª: Reparos Pós-venda 14/53 vs 15/51 (Δok=-1, Δtot=+2) — drift natural assimétrico.

### 5. Albérico Marinho — 3,91 (Vistoriador)

| Processo | Nota |
|---|---:|
| Vistorias (Laudo + Contestações) | 3,91 |

Indicadores:
- Laudos entregues ≤24h: 28/46 (baseline 28/36) — Δtot=+10 **DRIFT DE MODELO INTENCIONAL**.
- Contestações respondidas <24h: 4/23 (idêntico ao baseline).

---

## MUDANÇAS DE METODOLOGIA NA 11ª ED

A documentar no manual v5:

### 1. Marinho · Vistorias — Laudo conta tempo até saída da fase
Cards parados em "Em produção" depois do laudo entregue contam como atraso operacional.
**Justificativa:** o Marinho deve fechar o card no Pipefy assim que entrega o laudo — métrica é educativa, força disciplina de uso da ferramenta. A 10ª Ed excluía implicitamente esses casos.
**Impacto:** Δtot=+10 cards no denominador (esperado). Documentado em `baselines.json._aviso_drift_modelo`.

### 2. Vivianne · Inadimplência — Bônus por cobrança PROATIVA
Bônus só conta se a Vivianne abriu o card de cobrança **ANTES ou NO MESMO DIA** do pagamento (proativa) E a multa for compatível com atraso (≤15% do valor — exclui rescisões).
**Justificativa:** a 10ª Ed contava qualquer boleto com encargo pago antes do repasse, incluindo casos onde a Vivianne abriu o card depois (reativa). A nova regra reflete cobrança ativa real.
**Impacto:** N=124 → N=61, drift -63 INTENCIONAL. Documentado em `config/bonus_vivianne.json._aviso_drift_vs_baseline`.

### 3. Caio · Comercial — Bônus N=3 (revisão da 10ª + descarte de novos)
Continua os 3 IMs validados na 10ª (IM39, IM123, IM135). IM1567 saiu da janela 180d. 15 candidatos novos foram analisados pela gestora e descartados (11 por publicação anterior; 4 por entrada direta em ADM).
**Impacto:** N=4 → N=3 (perdeu IM1567).
Documentado em `config/bonus_caio.json.edicao_11_descartados`.

### 4. Gardênia · Cont. ADM — Fix de array vazio
"Criar Card de Vistoria Técnica" com valor `'[]'` (array vazio em formato string) era contado como preenchido. Agora exige conteúdo real.
**Impacto:** N=6 → N=5 (IM1845 excluído).

### 5. Assessoras · Rescisão Loc. — Refino da ordem de prioridade
Para identificar quando a assessora assumiu o caso, prioridade: (1) campo "Data do recebimento das chaves:" (com dois-pontos); (2) firstTimeIn da fase "CHAVES RECEBIDAS"; (3) fallback antigo (Vistoria recebida / Agendamento de vistoria out).
**Impacto numérico:** zero — a regra (2) não foi disparada nos dados atuais (todos os cards com fase preenchida também têm o campo). Salvaguarda implementada para o futuro.

---

## OFFs REAIS

**0** OFFs reais (bugs de modelo). ✓

Todos os deltas vs baseline 10ª têm explicação documentada (drift natural ou mudança de regra confirmada pela gestora).

---

## DRIFTS NATURAIS ACEITOS (10ª → 11ª Ed)

| Colaborador | Indicador | Calc | Baseline | Classificação |
|---|---|---|---|---|
| Vivianne | Renovação Confecção <4h | 11/23 | 9/21 | drift natural (+2/+2) |
| Vivianne | Inadimplência Cobrança <24h | 240/275 | 238/272 | drift natural (+2/+3) |
| Vivianne | Rescisão Loc. Taxas Final | 13/20 | 11/18 | drift natural (+2/+2) |
| Vivianne | BackOffice Concluído <24h | 103/148 | 101/146 | drift natural (+2/+2) |
| Natália | Reparos Pós-venda ≤7d | 14/53 | 15/51 | drift natural (-1/+2) |
| Caio | Tickets SLA | 749/1738 | 706/1686 | drift natural Octadesk (+43/+52) |
| Caio | WhatsApp Avals | 139/154 | 137/152 | drift natural Octadesk (+2/+2) |
| Outros indicadores | — | — | — | dentro de ±1 caso |

Total: **7 indicadores com drift natural aceito**, todos com ratio (%) próximo da baseline.

---

## MUDANÇAS DE MODELO COM IMPACTO INTENCIONAL

| Pessoa | Indicador | Δ | Origem |
|---|---|---|---|
| Marinho | Laudos ≤24h denominador | +10 cards | Regra 11ª (cards parados contam) |
| Vivianne | Bônus Inadimplência N | -63 (124→61) | Regra 11ª (cobrança proativa) |
| Caio | Bônus Comercial N | -1 (4→3) | IM1567 saiu da janela |
| Gardênia | Bônus Cont. ADM N | -1 (5→4 baseline, +1 11ª = 5) | Fix array vazio + drift |

---

## STATUS GERAL

**✓ Pipeline 100% operacional e pronto para Fase 5 (painel HTML)**.

Componentes:
- ✓ `pipeline/extract_pipefy.py` — 12 pipes Pipefy via GraphQL (cache em `dados/raw/`)
- ✓ `pipeline/extract_octadesk.py` — XLSX local de `dados/octadesk/` (Conversas, Tickets, Avaliações)
- ✓ `pipeline/extract_imobiliar.py` — CSVs Imobiliar com parser custom (multi-record)
- ✓ `calculate.py` — 30+ funções calc com regras do manual v4 + ajustes 11ª Ed
- ✓ `pipeline/validate.py` — comparação automática contra `baselines.json`
- ✓ `pipeline/run.py` — orquestrador end-to-end, gera `painel/dados/atual.json`

Configs persistidos para auditoria:
- ✓ `config/bonus_caio.json` (4 IMs 10ª, 3 continuação 11ª, 15 descartados com motivo)
- ✓ `config/bonus_vivianne.json` (N=61, regra R1+R2+R3, drift documentado)
- ✓ `baselines.json` (com `_aviso_drift_modelo` para Marinho)

Limitações conhecidas (não-bloqueantes para Fase 5):
- `painel/dados/atual.json` tem `IMOVEIS={}` e `PROC_RICH={}` vazios — drilldown por imóvel/processo fica para iteração futura.
- 38 cards no pipe Inadimplência sem "Vencimento 1º Boleto:" preenchido — Vivianne pode revisar.
- 8 cards Rescisão Loc. de cada assessora sem nenhum dos campos de chaves preenchidos — usam fallback antigo.

**Aprovado para iniciar Fase 5: criar `painel/index.html` (novo) consumindo `painel/dados/atual.json`, preservando `painel/index_v10_original.html` como referência.**

---

## STATUS FINAL

- ✅ Pipeline 100% operacional
- ✅ Painel HTML dinâmico funcionando (`painel/index.html` lê `painel/dados/atual.json`)
- ✅ Drilldown 55 chaves + 13 paineis PROC_RICH
- ✅ Edição 11 fechada e auditada em 14/05/2026

### Entregáveis finais

| Componente | Arquivo | Estado |
|---|---|---|
| Painel dinâmico | `painel/index.html` | ✅ operacional (455 KB) |
| Dados consumidos | `painel/dados/atual.json` | ✅ regenerado por `python pipeline/run.py` |
| Builder de drilldown (55 chaves) | `pipeline/imoveis_builder.py` | ✅ |
| Builder de PROC_RICH (13 paineis) | `pipeline/procrich_builder.py` | ✅ |
| Overrides de insights | `config/procrich_insights_overrides.json` | ✅ vazio (auto) |
| Backup pré-correção | `painel/index_quebrado_v1.html` | ✅ preservado (auditoria) |
| Referência 10ª Ed | `painel/index_v10_original.html` | ✅ intocado |

### Notas finais 11ª Edição

| Pos | Pessoa | Nota | Δ vs 10ª | Origem do delta |
|---:|---|---:|---:|---|
| 1 | Caio | 5,34 | -0,14 | drift natural + bônus IM1567 fora janela |
| 2 | Vivianne | 5,01 | -0,21 | regra Inadimplência (cobrança proativa) + drift |
| 3 | Natália ⬆ | 4,76 | +0,78 | regra Rescisão ADM (Caixa de entrada) |
| 4 | Gardênia ⬇ | 4,38 | +0,41 | regra Rescisão ADM + fix array vazio |
| 5 | Marinho | 3,91 | -0,85 | regra Vistorias (cards parados em "Em produção") |

---

## Correções pós-fechamento — 19/05/2026

### Problema reportado
O drilldown mostrava tempos absurdos no indicador **Rescisão ADM — Encerramento <4h** da Vivianne: IM737 com 462,9h (19 dias), IM1823 com 258h, IM1353 com 40h. Gestora confirmou que esses números não correspondem à realidade operacional.

### Causa-raiz
O cálculo usava `lastTimeOut − firstTimeIn` (campos `phases_history` do Pipefy). Quando um card **entra, sai e volta** para a mesma fase (cenário comum em Encerramento e Pendência Assessor), essa diferença engloba TODO o intervalo, incluindo o tempo em que o card estava em **outra** fase. O campo `phases_history.duration` (cumulativo, somente dentro da fase) já estava sendo extraído pelo pipeline mas não era usado por esses indicadores.

Marcador inequívoco: quando `firstTimeIn ≠ lastTimeIn`, o card passou pela fase mais de uma vez → diff superestima o tempo.

### Indicadores corrigidos (horas CORRIDAS)

| Função | Arquivo | Antes | Depois |
|---|---|---|---|
| `calc_vivianne_rescisao_adm` | `calculate.py` | `(col_out − col_in)` | `"Tempo total na fase Encerramento (dias)" × 24` |
| `vivi_resc_adm` (drilldown) | `pipeline/imoveis_builder.py` | `_gen_indicador_horas` | `_gen_indicador_tempo_col` |
| `calc_assessora_backoffice` | `calculate.py` | `(col_out − col_in)` | `"Tempo total na fase 🚩 Pendência Assessor (dias)" × 24` |
| `assessora_bo` (drilldown) | `pipeline/imoveis_builder.py` | diff inline | duration inline |

### Indicadores PAUSADOS (horas ÚTEIS — decisão técnica futura)

Mesmo padrão de risco, mas migrar para `duration` muda a semântica (Pipefy reporta tempo corrido, não útil). Precisam de tratamento: somar `duration` apenas dos trechos em horário útil (8h–18h, seg-sex).

- `calc_vivianne_contrato_adm` — Confecção do contrato <2h úteis
- `calc_assessora_contrato_adm` / `assessora_cadm` (drilldown) — Conferência do contrato úteis

### Impacto nas notas finais (snapshot 19/05/2026)

| Pessoa | Antes | Depois | Δ |
|---|---:|---:|---:|
| Caio | 5,38 | 5,38 | — |
| Vivianne | **4,99** | **5,24** | **+0,25** |
| Natália | 4,75 | 4,75 | — |
| Gardênia | 4,44 | 4,44 | — |
| Marinho | 3,82 | 3,82 | — |

Natália e Gardênia não tiveram alteração de nota: mesmo com o cálculo correto, todos os cards delas ainda passam de 24h na fase Pendência Assessor (problema operacional real, não bug de medição).

### Impacto por IM — Rescisão ADM Vivianne

| IM | Antes | Depois | Status antes | Status depois |
|---|---:|---:|:---:|:---:|
| IM737  | 462,9h | **30,2h** | ✗ | ✗ |
| IM1823 | 258,0h | **239,4h** | ✗ | ✗ |
| IM1353 | 40,4h  | **0,08h** | ✗ | **✓** (era falso-negativo) |
| IM1206 | 5,2h   | 5,2h     | ✗ | ✗ (sem reabertura) |
| IM1827 | 1,5h   | 1,5h     | ✓ | ✓ (sem reabertura) |

### Impacto por IM — BackOffice Pendência Assessor (cards onde houve reabertura)

| Pessoa | IM | Antes | Depois |
|---|---|---:|---:|
| Gardênia | IM1824 | 837,8h | **821,9h** |
| Gardênia | IM135  | 793,5h | **606,7h** |
| Gardênia | IM1782 | 542,7h | **351,0h** |

---

## Correção pós-fechamento — 27/05/2026 — Margem de Tolerância em Indicadores de HORAS

### Justificativa
O caso **IM1598** (Natália · Rescisão Loc. · Boleto prop <24h) levou **24h02min (24,05h)** — estourou a meta de 24h por ~3 minutos, mas era penalizado exatamente igual a um caso de 30h. A gestora aprovou (27/05/2026) uma **margem de tolerância de ~2% da meta** para absorver ruído operacional de poucos minutos, sem afrouxar metas de forma material.

### Regra aprovada
Tolerância somada à meta, **na mesma unidade** do tempo medido (corrida se a meta é corrida, útil se a meta é útil):

| Meta | Tolerância | Passa se tempo ≤ |
|---|---|---|
| 2h  | +5 min  | 2h05 |
| 4h  | +10 min | 4h10 |
| 12h | +14 min | 12h14 |
| 16h | +19 min | 16h19 |
| 24h | +30 min | 24h30 |
| 72h | +86 min | 73h26 |

Centralizada na constante `TOLERANCIAS` no topo de `calculate.py`; aplicada via helper `_meta_tol(meta)`.

### Aplicação
- **21 indicadores de horas** (corridas e úteis) em `calculate.py`.
- **17 drilldowns** correspondentes em `pipeline/imoveis_builder.py` — para que o ✓/✗ do drilldown bata com a pontuação (mesma origem do problema do IM1598).

### Exceções (tolerância NÃO aplicada)
- Indicadores em **dias** (ex.: Boleto final <15d, Pós-venda ≤7d, Ocupação <30d, CredPago ≤15d…).
- **BackOffice — Troca Titularidade <5d** (calculado em horas úteis, mas conceitualmente em dias).
- **WhatsApp — Resposta ≤5min** (minutos).
- **Vistorias — Produtividade ≥32 m²/h** (razão).
- Indicadores em **%** (avaliações WhatsApp/Tickets).

### Impacto nas notas finais (snapshot 27/05/2026, ref fixa = baseline)

| Pessoa | Antes | Depois | Δ |
|---|---:|---:|---:|
| Caio | 5,40 | **5,43** | +0,03 |
| Vivianne | 5,38 | **5,42** | +0,04 |
| Natália | 4,88 | **4,93** | +0,05 |
| Gardênia | 4,53 | **4,53** | +0,00 |
| Marinho | 3,84 | **3,94** | +0,10 |

Ranking inalterado. **BASELINE_9 (10ª Ed) NÃO foi alterado** — esta é uma correção pós-fechamento.

### Cards que mudaram de ✗ para ✓ (22 no total)

Cards de imóvel (5):

| Pessoa | Indicador | IM | Tempo real |
|---|---|---|---:|
| Caio | Comercial — Início <24h | IM357 | 24,12h |
| Caio | Cont. Loc. — Documentação <24h | IM391 | 24,25h |
| Vivianne | Rescisão Loc. — Levant. Taxas Prop <2h | IM1783 | 2,004h |
| Natália | Rescisão Loc. — Boleto prop <24h | **IM1598** | 24,05h |
| Marinho | Laudos ≤24h | IM1801 | 24,35h |

Tickets SLA <4h úteis (17 tickets): Caio +10, Vivianne +3, Natália +2, Gardênia +2.

### Indicador a indicador (ok/tot)

| Pessoa | Indicador | Antes | Depois |
|---|---|---:|---:|
| Caio | Comercial — Início <24h | 7/41 | 8/41 |
| Caio | Cont. Loc. — Documentação <24h | 25/41 | 26/41 |
| Caio | Tickets — SLA <4h | 803/1811 | 813/1811 |
| Vivianne | Rescisão Loc. — Levant. Prop <2h | 12/22 | 13/22 |
| Vivianne | Tickets — SLA <4h | 104/287 | 107/287 |
| Natália | Rescisão Loc. — Boleto prop <24h | 5/8 | 6/8 |
| Natália | Tickets — SLA <4h | 186/304 | 188/304 |
| Gardênia | Tickets — SLA <4h | 74/197 | 76/197 |
| Marinho | Laudos ≤24h | 29/49 | 30/49 |

