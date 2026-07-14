# Gera o instalador final (.exe) da Operação Assistida.
# Requer: ambiente virtual com pyinstaller instalado (requirements-dev.txt) e Inno Setup 6.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File installer\build.ps1 [-Version 1.0.0]

param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> Limpando builds anteriores..."
Remove-Item -Recurse -Force "$Root\build", "$Root\dist", "$Root\dist_installer" -ErrorAction SilentlyContinue

Write-Host "==> Empacotando com PyInstaller..."
& "$Root\env\Scripts\pyinstaller.exe" "$Root\installer\app.spec" --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$Iscc = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs", "C:\Program Files (x86)", "C:\Program Files" -Recurse -Filter "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $Iscc) { throw "ISCC.exe (Inno Setup) nao encontrado. Instale com: winget install -e --id JRSoftware.InnoSetup" }

Write-Host "==> Compilando instalador com Inno Setup..."
& $Iscc "$Root\installer\setup.iss" "/DMyAppVersion=$Version"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou" }

Write-Host "==> Pronto: $Root\dist_installer\OperacaoAssistida-Setup-$Version.exe"
