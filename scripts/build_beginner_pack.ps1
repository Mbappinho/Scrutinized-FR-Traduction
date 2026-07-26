# Assemble beginner pack under release\Scrutinized-FR-Beginner
# Copies currently patched files from the live Steam install.
param(
    [string]$LocRoot = (Split-Path $PSScriptRoot -Parent),
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $GameRoot) {
    $local = Join-Path $LocRoot "local_game_path.txt"
    if (Test-Path $local) {
        $GameRoot = (Get-Content $local -TotalCount 1).Trim().Trim('"')
    }
}
if (-not $GameRoot -or -not (Test-Path (Join-Path $GameRoot "Scrutinized.exe"))) {
    throw "Indique le jeu : -GameRoot 'C:\...\Scrutinized' ou local_game_path.txt"
}

$out = Join-Path $LocRoot "release\Scrutinized-FR-Beginner"
$filesOut = Join-Path $out "fichiers"
$scriptsOut = Join-Path $out "scripts"

# Files that differ from vanilla after full FR apply (must stay in sync with apply chain).
$rels = @(
    "Scrutinized_Data/globalgamemanagers",
    "Scrutinized_Data/Managed/Assembly-CSharp.dll",
    "Scrutinized_Data/Resources/browser_assets",
    "Scrutinized_Data/sharedassets0.assets",
    "Scrutinized_Data/sharedassets1.assets",
    "Scrutinized_Data/sharedassets3.assets",
    "Scrutinized_Data/sharedassets4.asset.res5",
    "Scrutinized_Data/sharedassets5.assets",
    "Scrutinized_Data/sharedassets9.assets",
    "Scrutinized_Data/level0",
    "Scrutinized_Data/level1",
    "Scrutinized_Data/level2",
    "Scrutinized_Data/level3",
    "Scrutinized_Data/level5",
    "Scrutinized_Data/level7",
    "Scrutinized_Data/level8",
    "Scrutinized_Data/level9"
)

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $filesOut, $scriptsOut | Out-Null

$listPath = Join-Path $filesOut "file_list.txt"
$lines = @("# Chemins relatifs a la racine du jeu (Scrutinized.exe)")
foreach ($rel in $rels) {
    $src = Join-Path $GameRoot ($rel -replace "/", "\")
    if (-not (Test-Path -LiteralPath $src)) { throw "Fichier manquant dans l'install : $src" }
    $dst = Join-Path $filesOut ($rel -replace "/", "\")
    New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
    Write-Host "Copy $rel ..."
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $lines += $rel
}
$lines | Set-Content -LiteralPath $listPath -Encoding UTF8

Copy-Item (Join-Path $LocRoot "scripts\beginner_common.ps1") $scriptsOut -Force
Copy-Item (Join-Path $LocRoot "scripts\install_fr_beginner.ps1") $scriptsOut -Force
Copy-Item (Join-Path $LocRoot "scripts\uninstall_fr_beginner.ps1") $scriptsOut -Force

$steamTarget = Join-Path $LocRoot "release\steam_target.json"
if (-not (Test-Path $steamTarget)) { throw "release\steam_target.json manquant" }
Copy-Item $steamTarget (Join-Path $out "steam_target.json") -Force

@'
@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Scrutinized FR - Installation
echo.
echo  Scrutinized - Traduction francaise (fan patch)
echo  Ferme le jeu avant de continuer.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_fr_beginner.ps1"
if errorlevel 1 pause
'@ | Set-Content -LiteralPath (Join-Path $out "INSTALLER.bat") -Encoding ASCII

@'
@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Scrutinized FR - Desinstallation
echo.
echo  Scrutinized - Retirer la traduction FR
echo  Ferme le jeu avant de continuer.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\uninstall_fr_beginner.ps1"
if errorlevel 1 pause
'@ | Set-Content -LiteralPath (Join-Path $out "DESINSTALLER.bat") -Encoding ASCII

@'
SCRUTINIZED - TRADUCTION FRANCAISE (FAN PATCH NON OFFICIEL)
==========================================================

1. Ferme Scrutinized completement.
2. Double-clique INSTALLER.bat
3. Choisis le dossier du jeu (souvent detecte tout seul)
4. Confirme avec O
5. Relance le jeu

Clavier : AZERTY (deplacement ZQSD).
Retirer la trad : DESINSTALLER.bat

Apres une MAJ Steam : verifie l'integrite, puis reinstalle ce pack
(ou telecharge une release plus recente si le BuildID a change).

Steam AppID 1384770 - voir steam_target.json pour le BuildID compatible.
'@ | Set-Content -LiteralPath (Join-Path $out "LIREMOI.txt") -Encoding UTF8

Write-Host ""
Write-Host "Pack pret : $out" -ForegroundColor Green
Get-ChildItem $filesOut -Recurse -File | Measure-Object Length -Sum |
    ForEach-Object { "Taille fichiers : {0:N0} Mo" -f ($_.Sum / 1MB) }
