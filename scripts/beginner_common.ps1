# Shared helpers for Scrutinized FR beginner install / uninstall.
$ErrorActionPreference = "Stop"

$Script:AppId = "1384770"
$Script:GameFolderName = "Scrutinized"
$Script:ExeName = "Scrutinized"
$Script:BackupDirName = "_ScrutinizedFR_backup_en"
$Script:MarkerName = ".scrutinized_fr_installed"
$Script:GithubRepo = "Mbappinho/Scrutinized-FR-Traduction"

function Write-Title([string]$Text) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Pause-Exit([int]$Code = 0) {
    Write-Host ""
    Write-Host "Appuie sur Entree pour fermer..."
    try { [void][System.Console]::ReadLine() } catch { }
    exit $Code
}

function Test-GameLooksValid([string]$Root) {
    if (-not $Root) { return $false }
    $exe = Join-Path $Root "Scrutinized.exe"
    $data = Join-Path $Root "Scrutinized_Data"
    return (Test-Path -LiteralPath $exe) -and (Test-Path -LiteralPath $data)
}

function Find-CandidateGameRoots {
    $candidates = New-Object System.Collections.Generic.List[string]
    $add = {
        param($p)
        if ($p -and (Test-Path -LiteralPath $p) -and (Test-GameLooksValid $p) -and -not $candidates.Contains($p)) {
            $candidates.Add($p) | Out-Null
        }
    }

    $steamRoots = @(
        "${env:ProgramFiles(x86)}\Steam\steamapps\common",
        "$env:ProgramFiles\Steam\steamapps\common",
        "C:\Steam\steamapps\common",
        "D:\SteamLibrary\steamapps\common",
        "E:\SteamLibrary\steamapps\common",
        "D:\Steam\steamapps\common",
        "E:\Steam\steamapps\common"
    )
    foreach ($lib in $steamRoots) {
        if (-not (Test-Path -LiteralPath $lib)) { continue }
        $hit = Join-Path $lib $Script:GameFolderName
        & $add $hit
        Get-ChildItem $lib -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Name -match "Scrutinized") { & $add $_.FullName }
        }
    }

    # libraryfolders.vdf
    $vdf = "${env:ProgramFiles(x86)}\Steam\steamapps\libraryfolders.vdf"
    if (Test-Path -LiteralPath $vdf) {
        $txt = Get-Content -LiteralPath $vdf -Raw -ErrorAction SilentlyContinue
        [regex]::Matches($txt, '"path"\s+"([^"]+)"') | ForEach-Object {
            $lib = Join-Path $_.Groups[1].Value.Replace("\\", "\") "steamapps\common"
            $hit = Join-Path $lib $Script:GameFolderName
            & $add $hit
        }
    }
    return $candidates
}

function Select-GameRoot {
    Write-Title "Dossier du jeu"
    $found = @(Find-CandidateGameRoots)
    if ($found.Count -gt 0) {
        Write-Host "Dossiers detectes :"
        for ($i = 0; $i -lt $found.Count; $i++) {
            Write-Host ("  [{0}] {1}" -f ($i + 1), $found[$i])
        }
        Write-Host "  [M] Entrer le chemin a la main"
        Write-Host ""
        $choice = Read-Host "Choix"
        if ($choice -match '^\d+$') {
            $idx = [int]$choice - 1
            if ($idx -ge 0 -and $idx -lt $found.Count) { return $found[$idx] }
        }
    } else {
        Write-Host "Aucun dossier Scrutinized detecte automatiquement."
        Write-Host ""
    }
    Write-Host "Exemple :"
    Write-Host '  C:\Program Files (x86)\Steam\steamapps\common\Scrutinized'
    Write-Host '  C:\Steam\steamapps\common\Scrutinized'
    Write-Host ""
    $manual = (Read-Host "Chemin complet du dossier du jeu").Trim().Trim('"')
    if (-not (Test-GameLooksValid $manual)) {
        throw "Ce dossier ne ressemble pas a Scrutinized (Scrutinized.exe / Scrutinized_Data manquants) : $manual"
    }
    return $manual
}

function Assert-GameClosed {
    $procs = Get-Process -Name $Script:ExeName -ErrorAction SilentlyContinue
    if ($procs) {
        Write-Host "Le jeu est encore ouvert. Ferme-le puis relance cet outil." -ForegroundColor Yellow
        throw "Jeu ouvert ($Script:ExeName)"
    }
}

function Get-PackRoot {
    $here = $PSScriptRoot
    # Pack layout: <pack>\scripts\this.ps1  +  <pack>\fichiers\...
    $packFromScripts = Resolve-Path (Join-Path $here "..") -ErrorAction SilentlyContinue
    if ($packFromScripts -and (Test-Path (Join-Path $packFromScripts "fichiers\file_list.txt"))) {
        return $packFromScripts.Path
    }
    # Dev: repo\release\Scrutinized-FR-Beginner
    $repo = Resolve-Path (Join-Path $here "..") -ErrorAction SilentlyContinue
    if ($repo) {
        $release = Join-Path $repo.Path "release\Scrutinized-FR-Beginner"
        if (Test-Path (Join-Path $release "fichiers\file_list.txt")) { return $release }
    }
    throw "Pack introuvable. Dezippe le pack Release ou lance : scripts\build_beginner_pack.ps1"
}

function Get-SteamTarget([string]$PackRoot) {
    $p = Join-Path $PackRoot "steam_target.json"
    if (-not (Test-Path -LiteralPath $p)) {
        $p = Join-Path $PackRoot "..\steam_target.json"
    }
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-SteamBuildId([string]$GameRoot) {
    $acf = Join-Path (Split-Path (Split-Path $GameRoot -Parent) -Parent) ("appmanifest_{0}.acf" -f $Script:AppId)
    # steamapps\common\Scrutinized -> steamapps\appmanifest
    $steamapps = Split-Path (Split-Path $GameRoot -Parent) -Parent
    $acf = Join-Path $steamapps ("appmanifest_{0}.acf" -f $Script:AppId)
    if (-not (Test-Path -LiteralPath $acf)) { return $null }
    $txt = Get-Content -LiteralPath $acf -Raw -ErrorAction SilentlyContinue
    $m = [regex]::Match($txt, '"buildid"\s+"(\d+)"')
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

function Test-SteamBuildCompatibility([string]$GameRoot, [string]$PackRoot) {
    $target = Get-SteamTarget $PackRoot
    $live = Get-SteamBuildId $GameRoot
    $packVer = if ($target -and $target.pack_version) { [string]$target.pack_version } else { "unknown" }
    $expected = if ($target -and $target.buildid) { [string]$target.buildid } else { $null }
    $status = "Unknown"
    if ($expected -and $live) {
        $status = if ($expected -eq $live) { "OK" } else { "Mismatch" }
    } elseif ($expected -and -not $live) {
        $status = "Unknown"
    }
    return [pscustomobject]@{
        Status       = $status
        Expected     = $expected
        Live         = $live
        PackVersion  = $packVer
        AppId        = $Script:AppId
    }
}

function Show-SteamBuildCheck($compat) {
    Write-Host ("Pack FR : v{0}" -f $compat.PackVersion)
    Write-Host ("BuildID attendu : {0}" -f $(if ($compat.Expected) { $compat.Expected } else { "?" }))
    Write-Host ("BuildID Steam   : {0}" -f $(if ($compat.Live) { $compat.Live } else { "introuvable" }))
    switch ($compat.Status) {
        "OK" { Write-Host "Compatibilite : OK" -ForegroundColor Green }
        "Mismatch" { Write-Host "Compatibilite : MAUVAIS BUILD (risque de crash / textes EN)" -ForegroundColor Red }
        default { Write-Host "Compatibilite : non verifiable" -ForegroundColor Yellow }
    }
}

function Get-FileList([string]$PackRoot) {
    $list = Join-Path $PackRoot "fichiers\file_list.txt"
    if (-not (Test-Path -LiteralPath $list)) { throw "file_list.txt manquant dans le pack" }
    Get-Content -LiteralPath $list -Encoding UTF8 |
        Where-Object { $_ -and $_.Trim() -and -not $_.Trim().StartsWith("#") } |
        ForEach-Object { $_.Trim().Replace("\", "/") }
}

function Backup-EnFiles([string]$GameRoot, [string]$PackRoot) {
    $backup = Join-Path $GameRoot "Scrutinized_Data\$Script:BackupDirName"
    $marker = Join-Path $GameRoot "Scrutinized_Data\$Script:MarkerName"
    if (Test-Path -LiteralPath $marker) {
        Write-Host "Backup EN deja present (reinstall FR) — on ne l'ecrase pas."
        return $backup
    }
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    foreach ($rel in Get-FileList $PackRoot) {
        $src = Join-Path $GameRoot ($rel -replace "/", "\")
        if (-not (Test-Path -LiteralPath $src)) {
            Write-Host "  (absent, ignore) $rel" -ForegroundColor Yellow
            continue
        }
        $dst = Join-Path $backup ($rel -replace "/", "\")
        $dstDir = Split-Path $dst -Parent
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Host "  backup EN: $rel"
    }
    return $backup
}

function Write-InstallMarker([string]$GameRoot, [string]$PackRoot) {
    $target = Get-SteamTarget $PackRoot
    $marker = Join-Path $GameRoot "Scrutinized_Data\$Script:MarkerName"
    $payload = @{
        pack_version = if ($target) { $target.pack_version } else { "dev" }
        buildid      = if ($target) { $target.buildid } else { $null }
        installed    = (Get-Date).ToString("s")
    } | ConvertTo-Json
    Set-Content -LiteralPath $marker -Value $payload -Encoding UTF8
}

function Install-FrFiles([string]$GameRoot, [string]$PackRoot) {
    $filesRoot = Join-Path $PackRoot "fichiers"
    foreach ($rel in Get-FileList $PackRoot) {
        $src = Join-Path $filesRoot ($rel -replace "/", "\")
        if (-not (Test-Path -LiteralPath $src)) { throw "Fichier manquant dans le pack : $rel" }
        $dst = Join-Path $GameRoot ($rel -replace "/", "\")
        $dstDir = Split-Path $dst -Parent
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Host "  FR -> $rel"
    }
}

function Uninstall-FrFiles([string]$GameRoot) {
    $backup = Join-Path $GameRoot "Scrutinized_Data\$Script:BackupDirName"
    $marker = Join-Path $GameRoot "Scrutinized_Data\$Script:MarkerName"
    if (-not (Test-Path -LiteralPath $backup)) {
        throw "Aucun backup EN local. Utilise Steam > Verifier l'integrite des fichiers."
    }
    $backupRoot = (Resolve-Path -LiteralPath $backup).Path
    Get-ChildItem -LiteralPath $backup -Recurse -File | ForEach-Object {
        $relFromBackup = $_.FullName.Substring($backupRoot.Length).TrimStart("\")
        $dst = Join-Path $GameRoot $relFromBackup
        $dstDir = Split-Path $dst -Parent
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $dst -Force
        Write-Host "  EN <- $relFromBackup"
    }
    if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker -Force }
    Remove-Item -LiteralPath $backup -Recurse -Force
}
