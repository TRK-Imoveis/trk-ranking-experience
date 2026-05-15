# PowerShell script para atualizar painel TRK em 1 comando
# Uso: cd para a pasta do projeto, depois ".\atualizar_painel.ps1"

Write-Host ""
Write-Host "🚀 Atualizando painel TRK..." -ForegroundColor Cyan
Write-Host ""

# 1. Rodar pipeline
Write-Host "[1/4] Rodando pipeline..." -ForegroundColor Yellow
python pipeline/run.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no pipeline. Abortando." -ForegroundColor Red
    exit 1
}

# 2. git add
Write-Host ""
Write-Host "[2/4] Adicionando arquivos..." -ForegroundColor Yellow
git add docs/dados/atual.json

# 3. git commit
$dataHoje = Get-Date -Format "yyyy-MM-dd"
Write-Host "[3/4] Fazendo commit (data: $dataHoje)..." -ForegroundColor Yellow
git commit -m "Atualizar dados $dataHoje"

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Nenhuma mudança detectada. Painel já está atualizado." -ForegroundColor Yellow
    exit 0
}

# 4. git push
Write-Host ""
Write-Host "[4/4] Enviando para o GitHub..." -ForegroundColor Yellow
git push

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Painel atualizado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Acessar: https://trk-imoveis.github.io/trk-ranking-experience/" -ForegroundColor Cyan
    Write-Host "⏰ Aguardar ~1 min para o painel atualizar online" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ Erro no push. Verifique sua conexão e tente novamente." -ForegroundColor Red
}
