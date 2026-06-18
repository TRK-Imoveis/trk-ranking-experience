# CHECKLIST PENDENTE — TRK Ranking Experience

Última atualização: 18/06/2026 (fechamento da 12ª Edição)

## ✅ Concluídas em 18/06/2026 (12ª Edição)
- [x] **Corrigir bug de horas ÚTEIS em cards reabertos** (era 🔴 ALTA, "latente" desde a 11ª — na verdade 73/265 cards reabertos na Confecção, 59/253 na Conferência). Novo helper `calculate.horas_uteis_fase`, aplicado em pontuação E drilldown (Armadilha 1). Impacto: Vivianne Confecção 11/27→20/29. Detalhe em `config/relatorio_edicao_12.md`.
- [x] **Cache do Pipefy estava congelado em 27/05** (daily rodava sem `--no-cache`). `atualizar_painel.ps1` corrigido para re-extrair o Pipefy a cada rodada.
- [x] **12ª Edição fechada e auditada** — relatório em `config/relatorio_edicao_12.md`. Baseline (BASELINE_9) atualizada para notas da 11ª; chaves `edicao_12` em configs.
- [x] **Bônus Caio · override IM143** validado pela gestora (alugado antes de publicação real).

## ✅ Concluídas em 27/05/2026
- [x] Investigar IM1598 (Rescisão Loc Natália) — diagnóstico: estouro de 3 min vs meta de 24h.
- [x] Aplicar margem de tolerância (~2%) em indicadores de horas (21 funções + 17 drilldowns).

## ✅ Concluídas em 15/05/2026
- [x] Criar organização TRK-Imoveis no GitHub
- [x] Transferir repositório para a organização
- [x] Renomear painel/ → docs/ (compatibilidade GitHub Pages)
- [x] Ativar GitHub Pages — URL: https://trk-imoveis.github.io/trk-ranking-experience/
- [x] **Atualizar Manual v4 → v5** — 6 mudanças metodológicas da 11ª Ed documentadas em `manual_v5.md` (727 linhas). v4 preservado como referência histórica. Nova §8 (Infraestrutura de Persistência) + apêndice 11ª Ed em §6.
- [x] **Criar guia de rotina diária + script PowerShell de automação** — `ROTINA_DIARIA.md` (passo-a-passo de 10 min) e `atualizar_painel.ps1` (1-comando: pipeline + add + commit + push). Gestora executa a rotina diária por conta própria a partir de hoje.

## Pendências da 11ª Edição

### Média prioridade
- [ ] **Configurar routines automáticas** na nuvem Anthropic (~30 min):
  - Snapshot diário 02h
  - Resumo semanal segunda 08h
  - Fechamento mensal dia 1 06h
  - Recalcular sob demanda (API)
  - Validação semanal sexta

### Média prioridade
- [ ] **🟡 Comunicar Caio** sobre cards parados nas colunas "dias desocupado" (Comercial). Na 12ª, 18/24 cards estavam exatamente um balde atrás (ex.: "60 Dias desocupado" devendo estar em "90") → indicador "Card na coluna correta" caiu de 15/27 para 1/24, principal motor da queda do Caio (−0,72). Espelha a regra do Marinho. Eventual tolerância de 1 balde fica como discussão futura.

### Baixa prioridade
- [ ] **Comunicar Marinho** sobre regra de cards parados em "Em produção" (não-técnico)
- [ ] **Refazer aba "Resumo Executivo"** com análises melhores quando quiser (escondida na 11ª)
- [ ] **Renomear BASELINE_9 → BASELINE_EDICAO_ANTERIOR** no código (cosmético, sem urgência)

## Pendências técnicas de qualidade

- [ ] **Atenção ao editar `atualizar_painel.ps1`**: o arquivo precisa estar salvo com UTF-8 BOM (Byte Order Mark). PowerShell 5.1 lê arquivos sem BOM como Windows-1252 e quebra caracteres acentuados. Ferramentas que strip BOM podem quebrar o script. Se houver erro de parsing, recriar o arquivo com `Set-Content -Encoding UTF8`.
- [x] ~~🔴 ALTA — Corrigir 3 indicadores de horas ÚTEIS com bug de duration cumulativo.~~ **RESOLVIDO na 12ª** via `calculate.horas_uteis_fase` (reconstrução por visita: exata p/ ≤2 visitas, aprox. documentada p/ 3+). Aplicado em `calc_vivianne_contrato_adm`, `calc_assessora_contrato_adm` e nos drilldowns `vivi_cadm`/`assessora_cadm`. A solução do CHECKLIST anterior ("somar duration dos trechos úteis") era inviável: o Pipefy reporta histórico AGREGADO por fase, sem os trechos individuais.
- [ ] **Investigar 7 boletos "passaram batido"** na Vivianne (cobrados antes do repasse, sem card aberto). Informação operacional útil — pode ser oportunidade perdida ou cliente que paga sem cobrança.
- [ ] **Reativar Produtividade m²/h do Marinho** quando metas forem recalibradas em conjunto com ele.

## Para a próxima edição (13ª)

- [ ] **Atualizar pasta dados/octadesk/** com XLSX recentes (Conversas, Tickets, Avaliações)
- [ ] **Atualizar pasta dados/csv/** com 3 CSVs recentes do Imobiliar (Boletos, Proprietários, Imóveis)
- [ ] **Rodar python pipeline/run.py --no-cache** (re-extrai Pipefy — NÃO esquecer o --no-cache)
- [ ] **Validar painel localmente** antes de commit
- [ ] **Validar candidatos a bônus Caio** (se houver novos IMs na lista pendente)
- [ ] **Atualizar baseline (BASELINE_9 em run.py) para as notas da 12ª** e renomear chaves edicao_12→edicao_13
- [ ] **Commit + push** com mensagem da edição

## ⚠️ Armadilhas técnicas conhecidas

Aprendizados consolidados — reler antes de mexer em regras de cálculo ou auditar IMs.

### Armadilha 1 — Duplicação `calculate.py` / `pipeline/imoveis_builder.py`
A lógica do teste de aprovação (✓/✗) está **duplicada em 2 lugares**:
- `calculate.py` → usado para a **PONTUAÇÃO** (nota do indicador).
- `pipeline/imoveis_builder.py` → usado para o **DRILLDOWN** (lista de cards no painel).

Mudar uma SEM mudar a outra gera inconsistência drilldown↔pontuação (um card aparece ✗ na lista mas conta como ✓ na nota, ou vice-versa).

**Procedimento:** sempre que alterar uma regra de aprovação (meta, tolerância, janela, filtro), verificar e atualizar os DOIS arquivos. Descoberto em 27/05/2026 ao aplicar a margem de tolerância (era a causa-raiz da contradição do IM1598).

### Armadilha 2 — Cards homônimos no Pipefy (mesmo IM, vários cards)
Imóveis recorrentes podem ter **múltiplos cards com o mesmo IM no título** ao longo do tempo (rescisões repetidas, troca de proprietário, recadastros etc.). Apenas o card da edição vigente entra no cálculo, mas os antigos poluem a auditoria.

Exemplo (27/05/2026): **IM1598** tinha 3 cards no pipe Rescisão de Locação — 2 de 2024 (Luiz Gustavo) + 1 de 2026 (Natália). Só o de 2026 entra no cálculo.

**Procedimento:** ao investigar um IM específico, SEMPRE conferir se há múltiplos cards no pipe (filtrar por título + olhar `Criado em` e `Assessor`) antes de assumir qual é o relevante.

---

**Como retomar:** abrir Claude Code com `claude --resume afc237db-430c-43c3-9826-f7e7ba90eac1` ou começar nova sessão e ler este arquivo.
