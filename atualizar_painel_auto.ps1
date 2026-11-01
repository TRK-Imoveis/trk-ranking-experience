# atualizar_painel_auto.ps1 - TRK Ranking
# Versao SEM interacao do atualizar_painel.ps1, para o Agendador de Tarefas do Windows.
# Faz exatamente o mesmo (git pull -> pipeline -> commit -> push), mas:
#   - entra sozinho na pasta do projeto
#   - grava tudo num log por dia em  %LOCALAPPDATA%\trk-ranking\logs\AAAA-MM-DD.log
#   - devolve o codigo de saida para o Agendador (0 = publicou ou nada mudou)
#
# Instalar (uma vez, no PowerShell, como seu usuario):
#   schtasks /Create /TN "TRK Ranking - atualizar painel" /SC DAILY /ST 09:00 /IT /F `
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\User\Documents\trk-ranking-experience\atualizar_painel_auto.ps1"
#
# Por que 09:00: o ETL do Pipefy carrega o dw_trk ~22h e ~10h; as 09:00 a rodada
# pega a carga da noite, com o notebook ja ligado na TRK. /IT = roda com a sua sessao (o git push usa a credencial
# do GitHub salva no Windows, que so abre com voce logada - a tela pode estar bloqueada).
#
# Ver as ultimas rodadas:  Get-ChildItem $env:LOCALAPPDATA\trk-ranking\logs | Sort-Object Name -Descending | Select-Object -First 5
# Rodar na mao agora:      schtasks /Run /TN "TRK Ranking - atualizar painel"

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $env:LOCALAPPDATA "trk-ranking\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ((Get-Date -Format "yyyy-MM-dd") + ".log")

Set-Location $repo
"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') inicio (auto) ====" | Out-File $log -Append -Encoding UTF8

# Sem rede ate o banco nao adianta nem comecar (notebook fora da TRK / VPN desligada)
$db = Test-NetConnection -ComputerName 192.168.64.106 -Port 5432 -WarningAction SilentlyContinue
if (-not $db.TcpTestSucceeded) {
    "ABORTADO: dw_trk (192.168.64.106:5432) inalcancavel - notebook fora da rede da TRK?" | Out-File $log -Append -Encoding UTF8
    exit 2
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "atualizar_painel.ps1") *>> $log
$rc = $LASTEXITCODE

# O pipeline grava o log detalhado em %TEMP%\trk_pipeline.log - copia os avisos que importam
$pipeLog = Join-Path $env:TEMP "trk_pipeline.log"
if (Test-Path $pipeLog) {
    Select-String -Path $pipeLog -Pattern "CAIU DE VOLTA|degradad|ETL do Pipefy|tem \d+ dias|pipefy\] lendo|ultima carga|última carga" |
        ForEach-Object { "  [pipeline] $($_.Line.Trim())" } | Out-File $log -Append -Encoding UTF8
}
"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') fim rc=$rc ====" | Out-File $log -Append -Encoding UTF8
exit $rc
