# TRK EXPERIENCE 2026 — Manual Técnico de Indicadores

**Ranking de Performance Operacional — Versão 5.0**

Período de avaliação: 180 dias correntes · Brasília · 2026

> Atualizado em 15/05/2026, após a 11ª Edição (maio/2026), consolidando mudanças
> metodológicas das 9ª, 10ª e 11ª Edições. As 9ª e 10ª foram edições de operação
> sem mudança metodológica formal (apenas drift de dados); todas as 6 mudanças
> abaixo foram introduzidas na 11ª Edição.
>
> **Mudanças v4 → v5 (11ª Ed):**
> - **Marinho Vistorias:** cards parados em "Em produção" contam como atraso (✗),
>   não como N/A. Decisão educativa: incentiva fechamento dos laudos. Ver §4.4.
> - **Vivianne Inadimplência:** N do bônus agora exige R1+R2+R3 estritos
>   (multa rescisão ≤15% E card.criado ≤ data_pag E data_pag ≤ data_repasse).
>   11ª Ed: N=61 (vs N=124 da regra antiga). Ver §4.2.
> - **Caio Comercial:** lista de IMs do bônus persistida em
>   `config/bonus_caio.json` (validação manual pela gestora vale para edições futuras
>   até alteração explícita). Ver §4.1.
> - **Gardênia Cont.ADM:** campo "Criar Card de Vistoria Técnica" preenchido com
>   array vazio `[]` (string literal do Pipefy) NÃO conta como preenchido. Ver §4.3.
> - **Rescisão ADM Assessoras:** início = `Última vez que saiu da fase Caixa de
>   entrada` (fallback: `Criado em`). Tempo na Caixa de entrada não é responsabilidade
>   da assessora. Ver §4.3.
> - **Rescisão Loc. (refinamento):** ordem de prioridade para campo início é
>   (1) `Data do recebimento das chaves:`, (2) `Primeira vez que entrou na fase CHAVES
>   RECEBIDAS`, (3) fallback antigo. Ver §4.3.
>
> **Mudanças v3 → v4 (8ª Ed):**
> - **Rescisão Loc. (Assessoras):** Boleto prop e Boleto final foram **redefinidos** — não usar mais `Criado em` nem fases "Gerar boleto"/"Negociação/Parcelamento" (cards pulam essas fases). Ver seção 4.3.
> - **Bônus Caio (Comercial):** sempre validar manualmente quando há suspeita de anúncio anterior ao período de 180d. Critério rigoroso: 1º Boleto preenchido + nenhum card do Comercial com anúncio em qualquer momento.
> - **Ocupação <30d (Caio):** excluir do denominador casos "alugado antes de re-anunciar" (1º Boleto anterior ao anúncio).


---

## 1. VISÃO GERAL

O Ranking TRK avalia 5 colaboradores em múltiplos processos operacionais.

### Colaboradores e processos

| Colaborador | Função | Processos |
|---|---|---|
| Caio Rodrigues Lima | Comercial | Com.Locação · Cont.Locação · Cont.ADM · Renovação · WhatsApp · Ticket |
| Albérico Marinho | Vistoriador | Vistorias · Contestações |
| Natália Teixeira | Assessora | Cont.ADM · Rescisão ADM · Rescisão Loc. · Reparos · Renovação · BackOffice · DIRF/DARF · WhatsApp · Ticket |
| Vivianne Fontes | BackOffice + Inadimplência | Cont.ADM · Rescisão ADM · Cont.Locação · Rescisão Loc. · Renovação · Inadimplência · BackOffice · Ticket |
| Gardênia | Assessora | Cont.ADM · Rescisão ADM · Rescisão Loc. · Reparos · Renovação · BackOffice · DIRF/DARF · WhatsApp · Ticket |

---

## 2. FÓRMULA DA NOTA FINAL

### Nota de cada processo

```
nota_processo = soma(scores dos indicadores do processo) ÷ soma(pesos do processo) × 10
```

Onde `score_indicador = (numerador / denominador) × peso`.

### Nota final do colaborador

```
nota_final = soma(notas dos processos) ÷ quantidade de processos com dados
```

Média simples das notas de processo. Processos sem dados (denominador = 0) são excluídos da média.

**⚠️ NUNCA usar soma ponderada global. NUNCA dividir pelo total de pesos de todos os indicadores.**

### Bônus

Alguns colaboradores têm bônus que se aplicam a um processo específico:

```
nota_processo_com_bonus = (score_base + N) ÷ (peso_base + N) × 10
```

Onde N = número de itens do bônus.

---

## 3. REGRAS GERAIS DE CÁLCULO

### 3.1 Cutoff do período
- **SEMPRE** 180 dias a contar da data de HOJE — nunca uma data fixa.
- Exemplo: se hoje é 28/04/2026, o cutoff é 30/10/2025.
- **Exceção:** Cont.ADM do Caio usa cutoff fixo = 01/03/2026.
- **Exceção:** DIRF/DARF usa filtro Ano = 2025.

### 3.2 Filtro de rascunhos
- Excluir cards onde qualquer campo de texto (Título, Imóvel, Endereço) contém "rascunho" (case insensitive).

### 3.3 Horas úteis
- Horário comercial: **08h00–18h00, segunda a sexta**.
- Usar SEMPRE que o indicador especificar "horas úteis" ou "dias úteis".
- Nunca usar campos pré-calculados do Octadesk/Pipefy para horas úteis — calcular manualmente.
- 1 dia útil = 10 horas úteis.

### 3.4 Tempo corrido (Pipefy)
- Quando o indicador especificar "tempo corrido" ou "coluna Pipefy", usar a coluna "Tempo total na fase X (dias)" diretamente.
- Converter para horas: valor × 24.

### 3.5 Timestamps negativos
- Quando a data de fim é anterior à data de início (timestamps invertidos), tratar como **0 horas** (= cumprido ✓).

### 3.6 WhatsApp — campo de tempo
- Usar coluna **"Tempo de espera após atribuição"**.
- Formato: HH:MM:SS. Converter para minutos.
- Filtro: coluna **"Responsável da conversa"** com nome exato.

### 3.7 WhatsApp — avaliações
- Coluna: **"Pesquisa de satisfação"** no relatório de conversas.
- **Excluir do denominador:** "Não respondeu" e "Não enviado".
- **Positivas:** "Satisfeito" + "Muito satisfeito".

### 3.8 Tickets — exclusões obrigatórias
Antes de calcular qualquer indicador de Ticket, aplicar TODAS estas exclusões:
1. Categoria de assunto = "Cancelado / Spam" → EXCLUIR
2. Status do ticket = "Cancelado" → EXCLUIR
3. Assunto do ticket = "Tarefa" (exato, case insensitive) → EXCLUIR

### 3.9 Tickets — SLA
- Calcular: `horas_uteis(Data de entrada, Data da primeira resposta)`
- Meta: ≤ 4 horas úteis.
- **NUNCA** usar campo de SLA pré-calculado do Octadesk.

### 3.10 Tickets — avaliações
- Fonte: arquivo `Avaliacoes-TICKET.xlsx`.
- Filtrar por "Responsável do ticket" com nome exato.
- **Positivas:** "Bom" + "Bom com comentário".
- Se colaborador não tem avaliações no arquivo, **excluir o indicador** (não entra no cálculo).

### 3.11 Filtro por agente — nomes exatos

| Colaborador | WhatsApp (Responsável da conversa) | Ticket (Responsável do ticket) |
|---|---|---|
| Caio | `Caio Rodrigues` | `Caio Rodrigues` (ou contains 'Caio') |
| Natália | `Natália Teixeira` | `Natália Teixeira` (ou contains 'Natália') |
| Gardênia | `Gardênia` | `Gardênia` (ou contains 'Gard') |
| Vivianne | **EXCLUÍDA do WhatsApp** | `Vivianne Fontes` ou `VIVIANNE FONTES` |

---

## 4. INDICADORES POR COLABORADOR

### 4.1 CAIO RODRIGUES LIMA — Comercial

**6 processos · Bônus: ★ imóvel alugado antes de ser anunciado (aplicado no Com.Locação)**

#### Comercial Locação (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 1 | Início <24h | `Criado em` | `Primeira vez que entrou na fase Avaliação Técnica` | ≤ 24h | Corrido | 2,5 |
| 2 | Anúncio <72h | `Última vez que saiu da fase Avaliação Técnica` (fallback: `Última vez que saiu da fase Cadastro / Reativação no NIDO`) | `Data publicação Anúncio` | ≤ 72h | Corrido | 2,5 |
| 3 | Coluna correta desocupação | Comparar fase atual do card vs fase esperada pelo nº dias desde publicação | — | Na fase correta | — | 5 |

**Regras específicas do Anúncio <72h:**
- **Denominador (Opção 3):** todos os cards que saíram da Aval.Téc OU foram publicados.
- **Liberação:** usar "Última vez que saiu da fase Avaliação Técnica". Se vazia, usar "Última vez que saiu da fase Cadastro / Reativação no NIDO" como fallback.
- **Negativos:** tratar como 0h (✓).
- **Filtro:** `Profissional responsável` contém "Caio".

**Regras específicas da Coluna correta:**
- **Denominador:** cards que passaram por "Conferência Final" E NÃO estão em "Concluído".
- **Dias desocupado:** hoje − `Data publicação Anúncio`.
- **Mapeamento de fases esperadas:**
  - 0–5 dias → Conferência Final
  - 6–29 dias → 15 dias desocupado
  - 30–59 dias → 30 Dias desocupado
  - 60–89 dias → 60 Dias desocupado
  - 90–179 dias → 90 Dias desocupado
  - 180+ dias → 180 Dias desocupado

**Bônus Caio (Comercial Locação):**
- N = número de imóveis alugados antes de serem anunciados.
- Fórmula: `(score_comercial + N) / (peso_comercial + N) × 10`

**⚠️ Critério rigoroso (validado na 8ª Ed):** um imóvel só conta no bônus se atender SIMULTANEAMENTE:
1. **Existe card no pipe Cont.Locação com `Primeira vez que entrou na fase 1º Boleto` preenchido** (contrato efetivamente formalizado — não basta ter card aberto).
2. **NENHUM card do pipe Comercial Caio para esse IM tem `Data publicação Anúncio` preenchida em qualquer momento** — não só dentro do período de 180d.
3. **Validação manual obrigatória:** o pipe Comercial só mostra cards do recorte atual. Se o IM teve anúncio em edições anteriores (anterior ao período de 180d), esse anúncio NÃO aparece nos dados, mas o imóvel não é elegível ao bônus. **Sempre perguntar ao usuário caso a caso** quando houver suspeita.

**Cards a considerar suspeitos (precisam validação manual):**
- IMs cujo 1º Boleto é de mais de ~6 meses atrás (provavelmente já tinham anúncio antes do período).
- IMs com múltiplos cards no Comercial e algum com anúncio publicado.

**11ª Ed (15/05/2026) — Persistência da validação manual:**
A lista de IMs validados (ou descartados) pela gestora é persistida em
`config/bonus_caio.json` e usada como fonte da verdade em edições futuras. O pipeline
não pede revalidação a cada execução — apenas sinaliza candidatos NOVOS (não presentes
na lista). Estrutura:
- `edicao_NN_continuacao`: IMs da edição anterior que ainda se aplicam.
- `edicao_NN_validados`: IMs novos aprovados.
- `edicao_NN_descartados`: IMs novos rejeitados com motivo (`por_publicacao_anterior`,
  `por_entrada_direta_em_ADM`, etc.).
- `edicao_NN_pendente`: IMs candidatos ainda não validados.

Exemplo 11ª Ed: 18 candidatos detectados, 3 validados (continuação da 10ª: IM39, IM123,
IM135), 15 descartados (11 com publicação anterior ao recorte, 4 com entrada direta
em ADM sem passar pelo Comercial). **N final = 3.**

#### Contrato Locação (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 4 | Ocupação <30d | `Data publicação Anúncio` (pipe Comercial) | `Primeira vez que entrou na fase 1º Boleto` (pipe Cont.Locação) | ≤ 30d | Corrido | 6 |
| 5 | Documentação completa 24h | `Criado em` | `Primeira vez que entrou na fase Confecção do contrato de locação` | ≤ 24h | **Úteis** | 4 |

**Regras específicas da Ocupação <30d:**
- **CRUZAMENTO ENTRE 2 PIPES** pelo campo IM.
- Pipe Comercial: extrair IM da coluna `IM` (numérica).
- Pipe Cont.Locação: extrair IM da coluna `Imóvel ` usando regex `IM\s*(\d+)` (case insensitive). Fallback: coluna `Título`.
- Publicação vem do Comercial, 1º Boleto vem do Cont.Locação.
- Denominador = IMs que aparecem em AMBOS os pipes.

**⚠️ Pareamento correto entre múltiplos anúncios e múltiplos boletos (8ª Ed):**
- Para cada `1º Boleto`, parear com o **anúncio anterior mais próximo** (não usar `max(anúncio)`).
- Se o IM tem anúncio (no período) que ocorreu **DEPOIS** do 1º Boleto, esse caso é "alugado antes de re-anunciar" — **EXCLUIR do denominador** (não há ocupação a medir; o aluguel não veio desse anúncio).
- Caso típico: IM357 na 8ª Ed (1º Boleto 22/12/2025, anúncio 24/04/2026 — re-locação após desocupação).

**Tratamento de casos sem anúncio no período:**
- IMs com 1º Boleto no período mas anúncio anterior ao recorte de 180d: o anúncio não aparece no pipe Comercial atual. Manter como está (não adicionar manualmente) — é uma limitação conhecida do recorte temporal.

**Regras específicas da Documentação 24h:**
- Usar **ENTRADA** na fase Confecção (não saída). Quando o card entra na Confecção, quem passa a atuar é a Vivianne — o tempo do Caio é até ali.

#### Contrato ADM (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 6 | Criação→NIDO <7d | `Criado em` | `Primeira vez que entrou na fase Contrato assinado - Conferir Nido` | < 7d | Corrido | 10 |

**Cutoff específico:** 01/03/2026 (NÃO 180 dias).

#### Renovação (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 7 | Avaliação >90d | — | `Data de vencimento` − `Última vez que saiu da fase Avaliação de mercado` | > 90d | Corrido | 10 |

**Indicador EXCLUSIVO do Caio. Natália e Gardênia NÃO têm este indicador.**

#### WhatsApp (peso total = 7)

| # | Indicador | Métrica | Meta | Peso |
|---|---|---|---|---|
| 8 | Resposta ≤5min | `Tempo de espera após atribuição` ≤ 5 minutos | ≤ 5 min | 4 |
| 9 | Avaliações positivas | "Satisfeito" + "Muito satisfeito" ÷ responderam | % positivas | 3 |

#### Ticket (peso total = 7)

| # | Indicador | Métrica | Meta | Peso |
|---|---|---|---|---|
| 10 | SLA ≤4h úteis | `horas_uteis(Data de entrada, Data da primeira resposta)` | ≤ 4h úteis | 4 |
| 11 | Avaliações positivas | "Bom" + "Bom com comentário" ÷ total (Avaliacoes-TICKET.xlsx) | % positivas | 3 |

---

### 4.2 VIVIANNE FONTES — BackOffice + Inadimplência

**8 processos · WhatsApp EXCLUÍDA · Bônus: cobrança antes do repasse (aplicado na Inadimplência)**

#### Contrato ADM (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 1 | Confecção <2h | `Primeira vez que entrou na fase Confecção do contrato` | `Última vez que saiu da fase Confecção do contrato` | ≤ 2h | **Úteis** | 10 |

#### Rescisão ADM (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 2 | Encerramento <4h | `Primeira vez que entrou na fase Encerramento` | `Última vez que saiu da fase Encerramento` | ≤ 4h | Corrido | 10 |

**⚠️ Este indicador é da Vivianne. O indicador "Repasse <12h" é das ASSESSORAS (Natália/Gardênia), não da Vivianne.**

#### Contrato Locação (peso total = 10)

| # | Indicador | Campo início / Coluna Pipefy | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 3a | NIDO→Concluído <24h | `Primeira vez que entrou na fase Fechamento NIDO` | `Primeira vez que entrou na fase Concluído` | ≤ 24h | Corrido | 5 |
| 3b | Confecção <2h | `Tempo total na fase Confecção do contrato de locação (dias)` × 24 | — | ≤ 2h (= ≤ 0,0833 dias) | **Corrido (Pipefy)** | 5 |

**⚠️ Confecção usa tempo CORRIDO da coluna Pipefy, NÃO calcular horas úteis.**

#### Rescisão Locação (peso total = 10)

| # | Indicador | Coluna Pipefy | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|
| 4a | Levant. Taxas Proporcionais <2h | `Tempo total na fase Levant. Taxas Proporcionais (dias)` × 24 | ≤ 2h | **Corrido (Pipefy)** | 5 |
| 4b | Levant. Taxas Final <2h | `Tempo total na fase Levantamento de taxas (dias)` × 24 | ≤ 2h | **Corrido (Pipefy)** | 5 |

**Vivianne só faz BackOffice na Rescisão Loc. (Levant. Taxas). NÃO tem indicadores de finalização (que são das assessoras).**

#### Renovação (peso total = 10)

| # | Indicador | Fonte | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|
| 5 | Confecção <4h | `Tempo total na fase Confecção do contrato (dias)` × 24 | ≤ 4h | **Corrido (Pipefy)** | 5 |
| 6 | Finalização <16h | `Primeira vez que entrou na fase Contrato assinado / Finalizar` → `Primeira vez que entrou na fase Processo concluído` | ≤ 16h | **Úteis** | 5 |

#### Inadimplência (peso total = 4)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 7 | Cobrança <24h | `Criado em` | `Primeira vez que entrou na fase Cobrança (inicial)` | ≤ 24h | Corrido | 2 |
| 8 | CredPago ≤15d | `Vencimento 1º Boleto:` | `Primeira vez que entrou na fase CredPago: Acionar` | ≤ 15d | Corrido | 1 |
| 9 | Negativação 7–9d | `Vencimento 1º Boleto:` | `Primeira vez que entrou na fase Negativação (No 8º dia de atraso)` | 7–9d | Corrido | 1 |

**⚠️ CredPago e Negativação usam "Vencimento 1º Boleto:" (com dois pontos) como data de início, NÃO "Criado em".**

**Bônus Inadimplência — "Boletos em atraso recebido antes do repasse":** N = boletos com encargo (multa adm OU juros adm) recebidos antes da data de repasse ao proprietário, validados pelas regras R1+R2+R3 (ver abaixo). Fórmula: `(score_inadim + N) / (peso_inadim + N) × 10`.

**⚠️ Cálculo do N — REGRA ESTRITA (11ª Ed):**

Cada boleto candidato precisa passar nas 3 regras simultaneamente:

- **R1 — Multa de rescisão ≤ 15% do valor:**
  `(Multa.Adm + Juros.Adm) ≤ 0.15 × Valor` — filtra fora rescisões cuja multa pode
  inflar artificialmente o numerador.

- **R2 — Card criado ≤ data do pagamento (date-only):**
  `card.Criado_em.date() ≤ Data_Pag.date()` — o card de cobrança precisa existir
  ANTES ou NO MESMO DIA do pagamento. Comparação por data (não timestamp): se o
  pagamento e a criação foram no mesmo dia, conta como cumprido (permissivo).
  Filtra fora cards "reativos" (criados depois do pagamento, sem cobrança real).

- **R3 — Pagamento ≤ data de repasse (date-only):**
  `Data_Pag.date() ≤ data_repasse.date()`. A `data_repasse` é calculada como:
  - mês/ano = mesmo mês do `Vencimento 1º Boleto:` do card
  - dia = `dia_pag` cadastrado no Proprietários CSV
  Comparação por data: pagamento no mesmo dia do repasse conta como cumprido.

**Pareamento card × boleto:**
- Cruzar por **IM + sub-contrato (1353/3)** OU por **Vencimento_1º_Boleto = mês do
  Data_Pag** quando o sub-contrato não está disponível.
- Se múltiplos cards no mesmo mês do mesmo IM, escolher o mais recente (`Criado_em`
  máximo).
- Cards sem `Vencimento 1º Boleto:` preenchido NÃO podem casar — registrar warning.

**Denominador para EXIBIÇÃO no dashboard =** todos os boletos com encargo que passaram
na R1 (filtro de multa) e têm proprietário com `dia_pag` cadastrado. Inclui:
- ✓ N (passam R1+R2+R3)
- ✗ Cards reativos (criados após o pagamento — falham R2)
- ✗ Pagos após o repasse (falham R3)
- ✗ Sem card no pipe Inadimplência (cobrados sem registro formal)

**Exemplo 11ª Ed:** 138 boletos passam R1 · 61 passam R1+R2+R3 (= N) · 7 reativos
· 15 após repasse · 55 sem card · 7 múltiplos no mesmo mês (escolhido mais recente).
Taxa exibida: 44,2%. **N usado na fórmula bônus = 61.**

> **Nota histórica:** a 8ª Ed usou regra mais frouxa (sem R2 explícita), N=84.
> Aplicar R1+R2+R3 nos dados da 8ª teria reduzido N para ~50. A mudança foi
> consciente: a regra antiga inflava o bônus com cards reativos.

#### BackOffice (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 10 | Concluído <24h | `Criado em` | `Primeira vez que entrou na fase Concluído` | ≤ 24h | Corrido | 5 |
| 11 | Troca Titularidade <5d | `Criado em` | `Primeira vez que entrou na fase Concluído` | ≤ 5d (50h) | **Úteis** | 5 |

**Regra:** Separar os cards pelo campo `Primeira vez que entrou na fase ↪️ Troca de Titularidade`:
- Cards SEM Troca de Titularidade → indicador 10 (Concluído <24h)
- Cards COM Troca de Titularidade → indicador 11 (Troca <5d úteis)

#### Ticket (peso total = 4)

| # | Indicador | Métrica | Meta | Peso |
|---|---|---|---|---|
| 12 | SLA ≤4h úteis | `horas_uteis(Data de entrada, Data da primeira resposta)` | ≤ 4h úteis | 4 |

**Avaliações de ticket EXCLUÍDAS (0 registros no período).**

---

### 4.3 NATÁLIA TEIXEIRA e GARDÊNIA — Assessoras

**9 processos cada · Bônus: ★ vistoria de entrada (aplicado no Cont.ADM)**

**Filtros de assessora por pipe:**

| Pipe | Coluna de filtro | Natália | Gardênia |
|---|---|---|---|
| Reparos | `Selecionar o assessor` | "Natália" | "Gardênia" ou "Gardenia" |
| Renovação | `Assessor (lista)` | "Natália" | "Gardênia" ou "Gardenia" |
| BackOffice | `Responsáveis` | contém "Natália" | contém "Gardenia" ou "Gardênia" |
| DIRF/DARF | `Responsáveis` | contém "Natália" | contém "Gardenia" ou "Gardênia" |
| Cont.ADM | Sem filtro (pipe compartilhado) | — | — |
| Rescisão ADM | Sem filtro (pipe compartilhado) | — | — |
| Rescisão Loc. | Sem filtro (pipe compartilhado) | — | — |

#### Contrato ADM (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 1 | Conferência ≤2h | `Primeira vez que entrou na fase Conferência do contrato` | `Última vez que saiu da fase Conferência do contrato` | ≤ 2h | **Úteis** | 10 |

**Bônus Vistoria de entrada:**
- Contar cards do Cont.ADM onde `Criar card de vistoria técnica` está preenchido, filtrado por `Assessor (lista)`.
- Natália: N = cards da Natália. Gardênia: N = cards da Gardênia.
- Fórmula: `(score_cadm + N) / (peso_cadm + N) × 10`

**⚠️ Fix array vazio (11ª Ed):** o Pipefy serializa campos do tipo array como string
literal. Quando o campo NÃO foi preenchido pelo usuário mas existe na fase, vem como
`'[]'` (string de array vazio JSON), e não como `None`/`NaN`. Tratar `'[]'` como
NÃO PREENCHIDO. Aplicar trim: `valor.strip() not in ('', '[]', 'null', None)`.
Caso encontrado na Gardênia (Edição 10): cards de vistoria contados a mais por essa
ambiguidade.

**Princípio operacional:** o sistema é responsável por interpretar corretamente
os valores do Pipefy (incluindo edge cases como `'[]'`). A gestora valida
exclusões/inclusões manuais apenas para casos onde a regra técnica não cobre
(ex: bônus Caio com anúncios anteriores ao recorte). Para o campo de vistoria,
a regra `strip() not in ('', '[]', 'null', None)` é definitiva.

#### Rescisão ADM (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 2 | Repasse <12h | `Última vez que saiu da fase Caixa de entrada` (fallback: `Criado em`) | `Primeira vez que entrou na fase Repasse final / Distrato (FINANCEIRO)` | ≤ 12h | **Úteis** | 5 |
| 3 | Distrato assinado | Campo `Termo de Distrato assinado` preenchido | — | Preenchido | — | 5 |

**Denominador do Distrato:** cards concluídos (`Primeira vez que entrou na fase Concluído` preenchido).

**⚠️ Início Repasse <12h (11ª Ed):** usar `Última vez que saiu da fase Caixa de
entrada` como início (quando preenchido), com fallback para `Criado em` se a fase
foi pulada. Justificativa: tempo na Caixa de entrada (triagem antes de chegar à
assessora) NÃO é responsabilidade dela. Impacto na 11ª Ed: Natália 0/2 → 2/2,
Gardênia 0/2 → 1/2 (cards saíram da Caixa de entrada e foram atendidos rapidamente).

#### Rescisão Locação (peso total = 5)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 4 | Boleto prop <24h | (1) `Data do recebimento das chaves:` OU (2) `Primeira vez que entrou na fase CHAVES RECEBIDAS` OU (3) `Última vez que saiu da fase Vistoria recebida` | `Primeira vez que entrou na fase Levant. Taxas Proporcionais` | ≤ 24h | Corrido | 2 |
| 5 | Boleto final <15d | (1) `Data do recebimento das chaves:` OU (2) `Primeira vez que entrou na fase CHAVES RECEBIDAS` OU (3) `Última vez que saiu da fase Agendamento de vistoria` | `Primeira vez que entrou na fase Envio do boleto final` | ≤ 15d | Corrido | 3 |

**⚠️ Regra de início (11ª Ed — 3 níveis de prioridade):**
- **Boleto prop:**
  1. `Data do recebimento das chaves:` (campo direto preenchido pela assessora)
  2. Se vazio: `Primeira vez que entrou na fase CHAVES RECEBIDAS` (evento de fase)
  3. Se vazio: `Última vez que saiu da fase Vistoria recebida` (fallback antigo)
- **Boleto final:** mesma ordem, com fallback (3) = `Última vez que saiu da fase
  Agendamento de vistoria`.

NÃO usar `Criado em` (tempo de vistoria/aguardando chaves NÃO é responsabilidade
da assessora).

**Impacto observado na 11ª Ed:** zero — todos os cards com fase CHAVES RECEBIDAS
preenchida também tinham o campo direto preenchido. Regra (2) é safeguard para
edições futuras.

**⚠️ Não usar fases "Gerar boleto" nem "Negociação/Parcelamento":** o fluxo Pipefy faz cards pularem essas fases, gerando NaT. As fases corretas para medição são `Levant. Taxas Proporcionais` (para boleto prop) e `Envio do boleto final` (para boleto final).

**⚠️ Negativos (Levant.Prop ou Envio boleto registrados antes do início):** tratar como 0h (= cumprido ✓). Comum no IM1783 e similares.

**⚠️ NÃO usar campos:** `Criado em` (mistura tempo de aguardando chaves), `Primeira vez fase Gerar boleto`, `Primeira vez fase Negociação/Parcelamento`, `Última vez saiu fase Orçamento`.

#### Reparos (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 6 | Orçamento <4h | `Criado em` | `Primeira vez que entrou na fase Orçamento \| Prestador` | ≤ 4h | **Úteis** | 4 |
| 7 | Finalização ≤7d | `Criado em` | `Primeira vez que entrou na fase Pós-venda` | ≤ 7d | Corrido | 6 |

**Filtrar por `Selecionar o assessor`** (NÃO "Assessor lista").
**⚠️ Usar "Pós-venda" como fase de fim — o card fica em Pós-venda até completar o período de avaliação do cliente. É a fase que marca a finalização efetiva do reparo pela assessora.**
**Denominador: cards do assessor no período que entraram na fase Pós-venda.**

#### Renovação (peso total = 10)

| # | Indicador | Métrica | Meta | Peso |
|---|---|---|---|---|
| 8 | Contato >60d antes vencimento | `Data de vencimento` − `Última vez que saiu da fase Contato com proprietário` | > 60d | 4 |
| 9 | Assinado antes do vencimento | `Primeira vez que entrou na fase Contrato assinado / Finalizar` < `Data de vencimento` | Antes do venc. | 6 |

**Filtrar por `Assessor (lista)`.**
**⚠️ Contato: usar "Última vez que SAIU da fase Contato com proprietário" (NÃO entrada, NÃO Locatário).**

#### BackOffice (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 10 | Pendência Assessor <24h | `Primeira vez que entrou na fase 🚩 Pendência Assessor` | `Última vez que saiu da fase 🚩 Pendência Assessor` | ≤ 24h | Corrido | 10 |

**Filtrar por coluna `Responsáveis`** (NÃO "Criador"). Usar arquivo que contenha essa coluna.

#### DIRF/DARF (peso total = 10)

| # | Indicador | Métrica | Meta | Peso |
|---|---|---|---|---|
| 11 | Concluído antes 01/mai | `Primeira vez que entrou na fase Concluído` < 01/05/ano corrente | Antes de 01/mai | 10 |

**Filtro:** `Ano:` = 2025 + coluna `Responsáveis` contém nome da assessora.
**Denominador:** TODOS os cards do ano 2025 da assessora (concluídos ou não).

#### WhatsApp (peso total = 7)

| # | Indicador | Meta | Peso |
|---|---|---|---|
| 12 | Resposta ≤5min | ≤ 5 min | 4 |
| 13 | Avaliações positivas | % positivas | 3 |

#### Ticket (peso total = 6)

| # | Indicador | Meta | Peso |
|---|---|---|---|
| 14 | SLA ≤4h úteis | ≤ 4h úteis | 3 |
| 15 | Avaliações positivas | % positivas (Bom + Bom c/ comentário) | 3 |

---

### 4.4 ALBÉRICO MARINHO — Vistoriador

**2 processos separados (Vistorias + Contestações). Cada um gera nota independente. Nota final = média das 2 notas.**

**⚠️ REGRA DE EXIBIÇÃO NO DASHBOARD (8ª Ed):**
Marinho aparece na tabela do ranking com **uma única coluna** ("Vistorias"), pois Contestações não é uma das 13 colunas de processos. Portanto:

1. Em `PESSOAS[marinho].scores`, manter os 2 processos: `Vistorias = nota_processo_vistorias` (ex: 3,70) e `Contestações = nota_processo_contestacoes` (ex: 1,74). Ambos preservados para alimentar:
   - Foco da Semana (alertas com nota < 2)
   - Resumo Executivo
   - Drawer/drilldown

2. No `renderRow` da tabela (função que pinta as células), aplicar uma exceção: quando `p.id === 'marinho'` E `proc === 'Vistorias'`, exibir `p.nota` (a nota final = 2,72) em vez de `p.scores['Vistorias']` (3,70). Usar **2 casas decimais** (em vez do padrão `toFixed(1)`) para casar visualmente com a coluna "Nota Final".

```javascript
let v = p.scores[proc];
if (p.id === 'marinho' && proc === 'Vistorias') v = p.nota;
// ...
const decimais = (p.id === 'marinho' && proc === 'Vistorias') ? 2 : 1;
v.toFixed(decimais).replace('.',',')
```

Resultado: tabela mostra "2,72" na coluna Vistorias do Marinho — idêntico à coluna "Nota Final".

3. **Painel PROC_RICH "Vistorias":** ao clicar na coluna Vistorias do Marinho, o painel deve mostrar os **3 indicadores** (Laudo + Produtividade + Contestações) — não apenas os 2 do processo Vistorias. O painel é único para o Marinho (já que ele só tem 1 coluna na tabela), então deve consolidar tudo.
   - KPIs: 4 cards (volume + 3 indicadores)
   - Bar-h: 3 indicadores
   - Indicadores detalhados: 3 linhas

No drilldown do drawer, manter os 3 indicadores separados (Laudo, Produtividade, Contestações).

#### Vistorias (peso total = 10)

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 1 | Laudo <24h | `Vistoria finalizada em` | `Última vez que saiu da fase Em produção` | ≤ 24h | **Úteis** | 4 |
| 2 | Produtividade ≥32 m²/h | `Área útil M²` ÷ horas entre `vistoria iniciada em` e `Vistoria finalizada em` | ≥ 32 m²/h | **Corrido** | 6 |

**Regras do Laudo:**
- Negativos (saiu de produção ANTES de finalizar vistoria) → tratar como 0h (✓).
- Usar `Vistoria finalizada em` como início (NÃO `Data da Vistoria`).
- **Cards ainda na fase "Em produção" — 11ª Ed:** quando `Última vez que saiu da
  fase Em produção` está vazia (card NÃO saiu da fase ainda), tratar como
  **atraso (✗)**, não como N/A. Justificativa: regra educativa para incentivar
  fechamento dos laudos. Cards parados em "Em produção" indicam laudo pendente
  por tempo indeterminado e devem contar contra o indicador.
- Implementação: cards sem saída de "Em produção" → fim = data de referência (`hoje`);
  cálculo `horas_uteis(Vistoria_finalizada, hoje)` retorna valor > 24h, falha a meta.

**Regras da Produtividade:**
- Tempo em horas CORRIDAS (NÃO úteis).
- Incluir vistorias de conferência de reparo no cálculo (puxam média para baixo — decisão do gestor).
- Excluir cards com `horas_vist` ≤ 0.

#### Contestações (peso total = 10) — PROCESSO SEPARADO

| # | Indicador | Campo início | Campo fim | Meta | Tipo tempo | Peso |
|---|---|---|---|---|---|---|
| 3 | Respondida <24h | `Criado em` | `Primeira vez que entrou na fase Concluído` | ≤ 24h | **Corrido** | 10 |

**Denominador:** cards que chegaram a Concluído.

---

## 5. ARQUIVOS NECESSÁRIOS

| Arquivo | Processo | Colunas obrigatórias extras |
|---|---|---|
| `ranking_trk___comercial_de_locao_XX.xlsx` | Comercial Locação (Caio) | `Data publicação Anúncio`, `IM` |
| `ranking_trk___contrato_de_locao_XX.xlsx` | Cont.Locação (Caio + Vivianne) | `Tempo total na fase Confecção do contrato de locação (dias)`, `Imóvel ` |
| `ranking_trk___contrato_de_administrao_XX.xlsx` | Cont.ADM (todos) | `Assessor (lista)`, `Criar card de vistoria técnica` |
| `ranking_trk___resciso_de_adm_XX.xlsx` | Rescisão ADM (Natália/Gardênia + Vivianne) | `Termo de Distrato assinado` |
| `ranking_trk___resciso_de_locao_XX.xlsx` | Rescisão Loc. (Assessoras + Vivianne) | `Tempo total na fase Levant. Taxas Proporcionais (dias)`, `Tempo total na fase Levantamento de taxas (dias)` |
| `trk_ranking___superviso_reparos_sx_XX.xlsx` | Reparos (Natália/Gardênia) | `Selecionar o assessor` |
| `ranking_trk__renovao_XX.xlsx` | Renovação (todos) | `Assessor (lista)`, `Tempo total na fase Confecção do contrato (dias)` |
| `superviso_inadimplncia___ranking_trk_XX.xlsx` | Inadimplência (Vivianne) | `Vencimento 1º Boleto:` |
| `ranking_trk___back_office_XX.xlsx` | BackOffice | `Responsáveis` (coluna obrigatória para filtrar assessora) |
| `ranking_trk___dirf_darf_XX.xlsx` | DIRF/DARF (Assessoras) | `Responsáveis`, `Ano:` |
| `ranking_trk___vistorias_XX.xlsx` | Vistorias (Marinho) | `vistoria iniciada em `, `Vistoria finalizada em`, `Área útil M²` |
| `contestao_de_vistorias___ranking_trk_XX.xlsx` | Contestações (Marinho) | — |
| `Total_de_conversas-XX.xlsx` | WhatsApp (Caio, Natália, Gardênia) | `Tempo de espera após atribuição`, `Pesquisa de satisfação`, `Responsável da conversa` |
| `Tickets_totais-XX.xlsx` | Tickets (todos exceto Marinho) | `Data da primeira resposta`, `Responsável do ticket`, `Categoria de assunto do ticket`, `Status do ticket`, `Assunto do ticket` |
| `Avaliacoes-TICKET.xlsx` | Avaliações Ticket | `Tipo de avaliação`, `Responsável do ticket` |
| Boletos CSV + Proprietários CSV + Imóveis CSV | Bônus Inadimplência Vivianne | Encoding latin-1, separador ';' |

---

## 6. RESULTADOS VALIDADOS — 8ª EDIÇÃO (REFERÊNCIA)

Estes são os resultados validados indicador-por-indicador em abril/2026.
Qualquer cálculo futuro deve reproduzir estes números quando usando os mesmos dados de entrada.

### Caio: 4,86

| Processo | Indicadores | Nota /10 |
|---|---|---|
| Com.Locação (c/ bônus ★1) | 5/39 · 23/46 · 8/14 | 4,93 |
| Cont.Locação | 5/8 · 28/49 | 6,04 |
| Cont.ADM | 1/3 | 3,33 |
| Renovação | 5/27 | 1,85 |
| WhatsApp | 1466/2600 · 122/136 | 7,07 |
| Ticket | 589/1474 · 18/21 | 5,96 |

### Vivianne: 4,94

| Processo | Indicadores | Nota /10 |
|---|---|---|
| Cont.ADM | 7/23 | 3,04 |
| Rescisão ADM | 2/4 | 5,00 |
| Cont.Locação | 11/40 · 40/49 | 5,46 |
| Rescisão Loc. | 10/18 · 8/16 | 5,28 |
| Renovação | 9/20 · 1/15 | 2,58 |
| Inadimplência (c/ bônus N=84) | 127/156 · 9/12 · 0/13 | 9,82 |
| BackOffice | 82/128 · 13/29 | 5,44 |
| Ticket | 76/264 | 2,88 |

### Natália: 3,25

| Processo | Indicadores | Nota /10 |
|---|---|---|
| Cont.ADM (c/ bônus ★4) | 3/22 | 3,83 |
| Rescisão ADM | 0/3 · 0/7 | 0,00 |
| Rescisão Loc. | 0/2 · 0/12 | 0,00 |
| Reparos | 43/55 · 14/56 | 4,63 |
| Renovação | 3/11 · 1/6 | 2,09 |
| BackOffice | 0/2 | 0,00 |
| DIRF/DARF | 8/30 | 2,67 |
| WhatsApp | 1759/2125 · 87/93 | 8,74 |
| Ticket | 148/238 · 20/24 | 7,28 |

### Gardênia: 2,75

| Processo | Indicadores | Nota /10 |
|---|---|---|
| Cont.ADM (c/ bônus ★3) | 3/22 | 3,36 |
| Rescisão ADM | 0/3 · 0/7 | 0,00 |
| Rescisão Loc. | 0/2 · 0/12 | 0,00 |
| Reparos | 43/61 · 13/36 | 4,99 |
| Renovação | 2/11 · 5/10 | 3,73 |
| BackOffice | 0/11 | 0,00 |
| DIRF/DARF | 0/7 | 0,00 |
| WhatsApp | 1722/2255 · 129/140 | 8,31 |
| Ticket | 53/190 · 3/5 | 4,39 |

### Marinho: 2,45

| Processo | Indicadores | Nota /10 |
|---|---|---|
| Vistorias | 27/45 · 5/39 | 3,17 |
| Contestações | 4/23 | 1,74 |

### 11ª EDIÇÃO (15/05/2026) — REFERÊNCIA ATUAL

| Pessoa | Nota Final | Bônus |
|---|---|---|
| Caio | 5,34 | N=3 (IM39, IM123, IM135 — continuação 10ª) |
| Vivianne | 5,01 | N=61 (R1+R2+R3 estrito) |
| Natália | 4,76 | N=5 (vistorias entrada) |
| Gardênia | 4,38 | N=5 (vistorias entrada) |
| Marinho | 3,91 | — |

Snapshot completo em `docs/dados/atual.json` (gerado por `python pipeline/run.py`).
Comparativo histórico: 9ª/10ª/11ª Eds têm relatórios detalhados em
`config/relatorio_edicao_NN.md`.

---

## 7. CHANGELOG

| Versão | Data | Alterações |
|---|---|---|
| 1.0 | 17/04/2026 | Versão inicial |
| 2.0 | 28/04/2026 | 30 correções após validação indicador-por-indicador. Reescrita completa. |
| **3.0** | **29/04/2026** | **7 correções: WhatsApp usa "Tempo de espera após atribuição"; Caio Documentação usa ENTRADA Confecção; Vivi Rescisão ADM = Encerramento <4h (não Repasse); Vivi Cont.Loc voltou 2 indicadores (NIDO+Confecção); Reparos usa Pós-venda (não Concluído); Renovação assessoras usa Saída Contato com proprietário; Resultados de referência atualizados.** |
| **5.0** | **15/05/2026** | **6 mudanças (9ª–11ª Ed): Marinho cards parados em "Em produção" contam como atraso; Vivianne Inadimplência R1+R2+R3 estritos; Caio bônus persistido em config/bonus_caio.json; Gardênia fix array vazio '[]'; Rescisão ADM início = saída Caixa de entrada; Rescisão Loc. nova prioridade CHAVES RECEBIDAS. Resultados 11ª Ed adicionados em §6. Nova §8 de Infraestrutura de Persistência.** |

---

## 8. INFRAESTRUTURA DE PERSISTÊNCIA (11ª Ed)

Esta seção documenta os arquivos de configuração e estado introduzidos na 11ª Ed.

Decisões metodológicas persistidas em arquivos JSON versionados no repositório.
Esta seção documenta cada arquivo, seu propósito e a interface esperada pelo pipeline.

### 8.1 config/bonus_caio.json

IMs do bônus Caio Comercial — validações manuais persistidas entre edições.
Estrutura: `edicao_NN_continuacao`, `edicao_NN_validados`, `edicao_NN_descartados`,
`edicao_NN_pendente`. Pipeline lê e respeita as validações sem perguntar novamente.
Detalhe das chaves descritas em §4.1.

### 8.2 config/bonus_vivianne.json

Snapshot da regra R1+R2+R3 da 11ª Ed com auditoria caso-a-caso (138 candidatos
pós-R1, decomposição em N=61 + reativos + após repasse + sem card). Não é insumo
do cálculo (o pipeline recalcula a cada execução) — serve para auditoria e
comparação entre edições.

### 8.3 config/procrich_insights_overrides.json

Sistema de overrides para insights dos paineis de processo no painel HTML.
Permite à gestora adicionar contexto humano a insights automáticos sem mexer
no código. Estrutura: `{processo: [{tipo, txt}]}`. Os insights customizados
aparecem ao lado dos automáticos no `procrich_builder.py`.

### 8.4 baselines.json

Notas de cada edição preservadas com avisos de drift documentados (chaves
`_aviso_drift_modelo`, `_aviso_drift_modelo_rescisao_adm` etc.). Usado para
deltas e identificação de mudanças metodológicas.
