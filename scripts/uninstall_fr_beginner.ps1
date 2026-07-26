# Remove French patch for Scrutinized (beginner-friendly).
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "beginner_common.ps1")

try {
    Write-Title "Scrutinized - Retirer la traduction FR"
    Write-Host "Ferme le jeu avant de continuer."
    Write-Host "Cet outil restaure le backup anglais cree a l'installation."
    Write-Host ""

    Assert-GameClosed
    $game = Select-GameRoot

    $backup = Join-Path $game "Scrutinized_Data\$BackupDirName"
    $marker = Join-Path $game "Scrutinized_Data\$MarkerName"

    Write-Host ""
    Write-Host "Desinstallation depuis :" -ForegroundColor Yellow
    Write-Host "  $game"
    if (-not (Test-Path -LiteralPath $backup)) {
        Write-Host ""
        Write-Host "Aucun backup EN trouve." -ForegroundColor Yellow
        Write-Host "Utilise Steam > Proprietes > Fichiers installes > Verifier l'integrite." -ForegroundColor Yellow
        Pause-Exit 1
    }
    Write-Host ""
    $ok = Read-Host "Confirmer la restauration EN ? (O/N)"
    if ($ok -notmatch '^[oOyY]') { throw "Annule." }

    Write-Host "Restauration des fichiers anglais..."
    Uninstall-FrFiles $game

    Write-Host ""
    Write-Host "OK - Traduction retiree. Le jeu devrait etre en anglais." -ForegroundColor Green
    Pause-Exit 0
}
catch {
    Write-Host ""
    Write-Host "ERREUR : $($_.Exception.Message)" -ForegroundColor Red
    Pause-Exit 1
}
