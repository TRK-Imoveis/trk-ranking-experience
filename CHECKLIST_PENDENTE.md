# CHECKLIST PENDENTE — TRK Ranking Experience

Última atualização: 27/05/2026 (margem de tolerância em indicadores de horas)

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

### Baixa prioridade
- [ ] **Comunicar Marinho** sobre regra de cards parados em "Em produção" antes da 12ª Edição (não-técnico)
- [ ] **Refazer aba "Resumo Executivo"** com análises melhores quando quiser (escondida na 11ª)
- [ ] **Renomear BASELINE_9 → BASELINE_EDICAO_ANTERIOR** no código (cosmético, sem urgência)

## Pendências técnicas de qualidade

- [ ] **Atenção ao editar `atualizar_painel.ps1`**: o arquivo precisa estar salvo com UTF-8 BOM (Byte Order Mark). PowerShell 5.1 lê arquivos sem BOM como Windows-1252 e quebra caracteres acentuados. Ferramentas que strip BOM podem quebrar o script. Se houver erro de parsing, recriar o arquivo com `Set-Content -Encoding UTF8`.
- [ ] **🔴 ALTA — Corrigir 3 indicadores de horas ÚTEIS com bug latente de duration cumulativo.** Mesmo padrão `(lastTimeOut − firstTimeIn)` corrigido em 19/05/2026 para horas corridas (Rescisão ADM + BackOffice). Para horas úteis, migrar para `duration` muda a semântica (Pipefy reporta tempo corrido). Solução pendente: somar `duration` apenas dos trechos em horário comercial (8h–18h, seg-sex). Funções afetadas:
  - `calc_vivianne_contrato_adm` — Confecção do contrato <2h úteis (`calculate.py`)
  - `calc_assessora_contrato_adm` — Conferência do contrato úteis (`calculate.py`)
  - `assessora_cadm` (drilldown) — Conferência do contrato úteis (`pipeline/imoveis_builder.py`)
  - Ver detalhes em `config/relatorio_edicao_11.md` → "Correções pós-fechamento — 19/05/2026".
- [ ] **Investigar 7 boletos "passaram batido"** na Vivianne (cobrados antes do repasse, sem card aberto). Informação operacional útil — pode ser oportunidade perdida ou cliente que paga sem cobrança.
- [ ] **Reativar Produtividade m²/h do Marinho** quando metas forem recalibradas em conjunto com ele.

## Para a próxima edição (12ª)

- [ ] **Atualizar pasta dados/octadesk/** com XLSX recentes (Conversas, Tickets, Avaliações)
- [ ] **Atualizar pasta dados/csv/** com 3 CSVs recentes do Imobiliar (Boletos, Proprietários, Imóveis)
- [ ] **Rodar python pipeline/run.py** (apenas comando)
- [ ] **Validar painel localmente** antes de commit
- [ ] **Validar candidatos a bônus Caio** (se houver novos IMs na lista pendente)
- [ ] **Commit + push** com mensagem da edição

---

**Como retomar:** abrir Claude Code com `claude --resume afc237db-430c-43c3-9826-f7e7ba90eac1` ou começar nova sessão e ler este arquivo.
