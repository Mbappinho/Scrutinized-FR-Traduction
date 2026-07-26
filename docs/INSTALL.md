# Installation joueur (Scrutinized FR)

## Pack Release

Version actuelle : **1.0.2** (scripts PowerShell ASCII + UTF-8 BOM, compatibles Windows PowerShell 5.1).

1. Télécharger `Scrutinized-FR-Traduction.zip` depuis les Releases GitHub (**v1.0.2** ou plus).
2. Supprimer les anciens dossiers dézippés sur le Bureau (ex. `Scrutinized-FR-Traduction (1)`).
3. Fermer le jeu.
4. Lancer `INSTALLER.bat`.
5. Choisir le dossier contenant `Scrutinized.exe`.
6. Confirmer.

Un dossier `Scrutinized_Data\_ScrutinizedFR_backup_en\` est créé au premier install
(copie EN). `DESINSTALLER.bat` le restaure.

### Dépannage parse PowerShell

Si `INSTALLER.bat` / `DESINSTALLER.bat` affiche `TerminatorExpectedAtEndOfString` ou
« terminateur " manquant », le pack est trop ancien (v1.0.0 / v1.0.1) ou corrompu :
retélécharger **v1.0.2**.

## BuildID

Voir [`release/steam_target.json`](../release/steam_target.json).  
Si Steam a mis à jour le jeu, attendre une release FR pour ce BuildID.

## Désinstallation sans backup

Steam → Propriétés → Fichiers installés → **Vérifier l’intégrité des fichiers**.

## Contenu du pack (`fichiers/`)

Fichiers Unity / DLL / SQLite / browser_assets déjà patchés (pas besoin de Python).
