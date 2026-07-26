# Installation joueur (Scrutinized FR)

## Pack Release

1. Télécharger `Scrutinized-FR-Traduction.zip` depuis les Releases GitHub.
2. Fermer le jeu.
3. Lancer `INSTALLER.bat`.
4. Choisir le dossier contenant `Scrutinized.exe`.
5. Confirmer.

Un dossier `Scrutinized_Data\_ScrutinizedFR_backup_en\` est créé au premier install
(copie EN). `DESINSTALLER.bat` le restaure.

## BuildID

Voir [`release/steam_target.json`](../release/steam_target.json).  
Si Steam a mis à jour le jeu, attendre une release FR pour ce BuildID.

## Désinstallation sans backup

Steam → Propriétés → Fichiers installés → **Vérifier l’intégrité des fichiers**.

## Contenu du pack (`fichiers/`)

Fichiers Unity / DLL / SQLite / browser_assets déjà patchés (pas besoin de Python).
