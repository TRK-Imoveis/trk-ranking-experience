# CHECKLIST PENDENTE — TRK Ranking Experience

Última atualização: 15/05/2026 (Manual v5 publicado)

## ✅ Concluídas em 15/05/2026
- [x] Criar organização TRK-Imoveis no GitHub
- [x] Transferir repositório para a organização
- [x] Renomear painel/ → docs/ (compatibilidade GitHub Pages)
- [x] Ativar GitHub Pages — URL: https://trk-imoveis.github.io/trk-ranking-experience/
- [x] **Atualizar Manual v4 → v5** — 6 mudanças metodológicas da 11ª Ed documentadas em `manual_v5.md` (727 linhas). v4 preservado como referência histórica. Nova §8 (Infraestrutura de Persistência) + apêndice 11ª Ed em §6.

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
