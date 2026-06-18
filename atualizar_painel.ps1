# atualizar_painel.ps1 — TRK Ranking
# Atualizacao do painel em 1 comando
# Uso: cd para a pasta do projeto, depois ".\atualizar_painel.ps1"

# Evita que git abra editor (Vim) em merges automaticos
$env:GIT_MERGE_AUTOEDIT = "no"

$DisplayNames = @{
    "caio"     = "Caio"
    "vivianne" = "Vivianne"
    "natalia"  = "Natália"
    "gardenia" = "Gardênia"
    "marinho"  = "Marinho"
}

function Show-Ranking {
    param($PostData, $PreData)
    $pre = @{}
    if ($PreData -and $PreData.PESSOAS) {
        foreach ($p in $PreData.PESSOAS) { $pre[$p.id] = $p.nota }
    }
    Write-Host ""
    Write-Host "📊 Notas finais:" -ForegroundColor Cyan
    $sorted = $PostData.PESSOAS | Sort-Object pos
    foreach ($p in $sorted) {
        $nome = $DisplayNames[$p.id]
        if (-not $nome) { $nome = $p.nome }
        $delta = ""
        if ($pre.ContainsKey($p.id)) {
            $d = [math]::Round($p.nota - $pre[$p.id], 2)
            if ($d -gt 0)     { $delta = "  (+$d)" }
            elseif ($d -lt 0) { $delta = "  ($d)" }
            else              { $delta = "  (sem mudança)" }
        }
        $linha = "{0}. {1,-10} {2,5:N2}{3}" -f $p.pos, $nome, $p.nota, $delta
        Write-Host "   $linha"
    }
}

Write-Host ""
Write-Host "🚀 Atualizando painel TRK..." -ForegroundColor Cyan
Write-Host ""

# Pre-check: pasta correta
if (-not (Test-Path "pipeline/run.py")) {
    Write-Host "❌ Este script precisa rodar na pasta do projeto." -ForegroundColor Red
    Write-Host "   Esperava encontrar: pipeline\run.py" -ForegroundColor Gray
    Write-Host "   Pasta atual: $(Get-Location)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Solução: rode antes:" -ForegroundColor Yellow
    Write-Host "      cd C:\Users\trkim\Documents\trk-ranking-experience" -ForegroundColor Yellow
    exit 1
}

# Captura estado pre-pipeline (para mostrar delta no final)
$preData = $null
if (Test-Path "docs/dados/atual.json") {
    try {
        $preData = Get-Content "docs/dados/atual.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { $preData = $null }
}

# [1/5] git pull
Write-Host "[1/5] Sincronizando com o GitHub..." -ForegroundColor Yellow
$pullLog = Join-Path $env:TEMP "trk_git_pull.log"
git pull --no-edit --ff-only *> $pullLog
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "⚠️  Houve divergência entre seu PC e o GitHub que não posso resolver sozinho." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Isso é raro mas pode acontecer. Para resolver:" -ForegroundColor Yellow
    Write-Host "   1. Abra uma nova sessão do Claude Code (claude --resume <sessionID>)" -ForegroundColor Yellow
    Write-Host "   2. Cole: 'Tenho divergência git no projeto, me ajude a resolver'" -ForegroundColor Yellow
    Write-Host "   3. O Claude vai te guiar passo a passo" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Log salvo em: %TEMP%\trk_git_pull.log" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Se preferir, copie o erro acima e mande para a assistente IA do projeto." -ForegroundColor Gray
    exit 1
}
$pullOut = Get-Content $pullLog -Raw -ErrorAction SilentlyContinue
if ($pullOut -match "Already up to date|Já está atualizado") {
    Write-Host "   ✓ Já estava atualizado." -ForegroundColor Green
} else {
    Write-Host "   ✓ Mudanças recentes do GitHub baixadas." -ForegroundColor Green
}

# [2/5] pipeline
Write-Host ""
# --no-cache: re-extrai os 12 pipes do Pipefy a cada rodada (~2-3 min). Sem isso o
# cache de dados/raw/ congela e os indicadores do Pipefy param de atualizar (bug que
# congelou os dados entre 27/05 e 18/06/2026). Octadesk/CSV são sempre lidos do disco.
Write-Host "[2/5] Rodando pipeline com dados frescos do Pipefy (~2-3 min)..." -ForegroundColor Yellow
$logFile = Join-Path $env:TEMP "trk_pipeline.log"
python pipeline/run.py --no-cache *> $logFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no pipeline." -ForegroundColor Red
    Write-Host "   Últimas 20 linhas do log:" -ForegroundColor Gray
    Get-Content $logFile -Tail 20 | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
    Write-Host ""
    Write-Host "   Log completo em: $logFile" -ForegroundColor Gray
    exit 1
}
Write-Host "   ✓ docs/dados/atual.json gerado" -ForegroundColor Green

# [3/5] git add
Write-Host ""
Write-Host "[3/5] Adicionando arquivos..." -ForegroundColor Yellow
git add docs/dados/atual.json 2>$null
$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Write-Host "   ⚠️  Nenhuma mudança detectada. Painel já está atualizado." -ForegroundColor Yellow
    try {
        $postData = Get-Content "docs/dados/atual.json" -Raw -Encoding UTF8 | ConvertFrom-Json
        Show-Ranking $postData $preData
    } catch {}
    Write-Host ""
    Write-Host "🌐 Painel: https://trk-imoveis.github.io/trk-ranking-experience/" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}
$plural = if ($staged.Count -eq 1) { "arquivo modificado" } else { "arquivos modificados" }
Write-Host "   ✓ $($staged.Count) $plural" -ForegroundColor Green

# [4/5] commit
$dataHoje = Get-Date -Format "yyyy-MM-dd"
Write-Host ""
Write-Host "[4/5] Fazendo commit..." -ForegroundColor Yellow
git commit -m "Atualizar dados $dataHoje" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no commit. Verifique 'git status'." -ForegroundColor Red
    exit 1
}
$hashShort = git rev-parse --short HEAD
Write-Host "   ✓ [main $hashShort] Atualizar dados $dataHoje" -ForegroundColor Green

# [5/5] push
Write-Host ""
Write-Host "[5/5] Enviando para o GitHub..." -ForegroundColor Yellow
git push 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro no push. Verifique sua conexão." -ForegroundColor Red
    Write-Host "   O commit foi feito localmente. Tente 'git push' manualmente depois." -ForegroundColor Gray
    exit 1
}
Write-Host "   ✓ Push concluído" -ForegroundColor Green

# Resumo final
$postData = Get-Content "docs/dados/atual.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Show-Ranking $postData $preData

Write-Host ""
Write-Host "🌐 Painel: https://trk-imoveis.github.io/trk-ranking-experience/" -ForegroundColor Cyan
Write-Host "   (atualiza em ~1 minuto)" -ForegroundColor Gray
Write-Host ""
