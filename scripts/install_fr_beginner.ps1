# Install French patch for Scrutinized (beginner-friendly).
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "beginner_common.ps1")

try {
    Write-Title "Scrutinized - Installer la traduction FR"
    Write-Host "Ferme le jeu avant de continuer."
    Write-Host "Cet outil remplace des fichiers du jeu par la version FR."
    Write-Host "Un backup anglais est cree automatiquement (desinstallation possible)."
    Write-Host "AZERTY (ZQSD) inclus. Patch non officiel."
    Write-Host ""

    Assert-GameClosed
    $pack = Get-PackRoot
    $game = Select-GameRoot

    $compat = Test-SteamBuildCompatibility $game $pack
    Show-SteamBuildCheck $compat
    Write-Host ""

    if ($compat.Status -eq "Mismatch") {
        $force = Read-Host "Installer QUAND MEME malgre le mauvais BuildID ? (O/N)"
        if ($force -notmatch '^[oOyY]') { throw "Annule - telecharge une release FR pour ton BuildID Steam." }
        Write-Host "Installation forcee (risque de crash)." -ForegroundColor Yellow
    } elseif ($compat.Status -eq "Unknown") {
        $cont = Read-Host "Continuer sans verification BuildID ? (O/N)"
        if ($cont -notmatch '^[oOyY]') { throw "Annule." }
    }

    Write-Host ""
    Write-Host "Installation vers :" -ForegroundColor Yellow
    Write-Host "  $game"
    Write-Host ""
    $ok = Read-Host "Confirmer ? (O/N)"
    if ($ok -notmatch '^[oOyY]') { throw "Annule." }

    Write-Host "Sauvegarde des fichiers anglais..."
    Backup-EnFiles $game $pack | Out-Null

    Write-Host "Copie des fichiers FR..."
    Install-FrFiles $game $pack
    Write-InstallMarker $game $pack

    Write-Host ""
    Write-Host "OK - Traduction installee. Lance Scrutinized." -ForegroundColor Green
    Write-Host "Pour retirer : DESINSTALLER.bat" -ForegroundColor Green
    Pause-Exit 0
}
catch {
    Write-Host ""
    Write-Host "ERREUR : $($_.Exception.Message)" -ForegroundColor Red
    Pause-Exit 1
}
