# 🌙 Rotina Diária TRK — Atualizar Painel

**Tempo total: ~10 minutos**

## Passo 1 — Baixar Octadesk (5 min)
1. Abrir https://app.octadesk.com
2. Para cada relatório abaixo, baixar XLSX dos últimos 180 dias:
   - Conversas
   - Tickets
   - Avaliações
3. Salvar em: `C:\Users\trkim\Documents\trk-ranking-experience\dados\octadesk\`
4. APAGAR os XLSX antigos da pasta (manter só o mais recente de cada tipo)

## Passo 2 — Baixar Imobiliar (3 min)
1. Abrir Imobiliar Connect
2. Baixar 3 CSVs:
   - Relatório de Boletos Quitados
   - Relatório De Proprietários
   - Relatório de Imóveis
3. Salvar em: `C:\Users\trkim\Documents\trk-ranking-experience\dados\csv\`
4. APAGAR os CSVs antigos da pasta

## Passo 3 — Atualizar Painel (2 min)
Abrir PowerShell e rodar:

```powershell
cd C:\Users\trkim\Documents\trk-ranking-experience
.\atualizar_painel.ps1
```

OU, se preferir comandos manuais:

```powershell
cd C:\Users\trkim\Documents\trk-ranking-experience
python pipeline/run.py
git add docs/dados/atual.json
git commit -m "Atualizar dados $(Get-Date -Format yyyy-MM-dd)"
git push
```

## Passo 4 — Conferir (30 seg)
1. Aguardar 1-2 min
2. Abrir https://trk-imoveis.github.io/trk-ranking-experience/
3. Confirmar que mudou (data ou alguma nota diferente)

---

## ⚠️ Problemas comuns

**"python: command not found"**
→ Verificar se Python está instalado. Provavelmente sim, mas o PATH pode estar diferente. Usa `python3` em vez de `python`.

**"Permission denied" no git push**
→ Token de autenticação expirou. Pedir ajuda ao desenvolvedor.

**"No changes added to commit"**
→ O `python pipeline/run.py` não gerou diferença (raro). Confere se os arquivos novos estão nas pastas dados/.

**"Painel não atualiza"**
→ Esperar 2 min e dar Ctrl+F5 no navegador (sem cache).
