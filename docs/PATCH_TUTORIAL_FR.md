# Patch tutos FR (browser_assets)

## Statut

Lot **P0** appliqué sur l’install Steam locale (BuildID `20456853`) :

- `Tutorial.html` → FR
- `TutorialControls.html` → FR
- `Foundation.css` → inchangé (pas de texte)

## Appliquer / restaurer

```powershell
cd C:\Users\kaoth\Projects\Scrutinized-FR

# Dry-run
python scripts\patch_browser_assets_fr.py --dry-run

# Patch jeu (backup auto dans backup/)
python scripts\patch_browser_assets_fr.py --apply

# Restaurer dernier backup EN
python scripts\patch_browser_assets_fr.py --restore
```

Sources FR : [`work/p0/html/`](../work/p0/html/).

Après le patch HTML, repeindre les touches **ZQSD** :

```powershell
python scripts\patch_tutorial_keys_azerty.py --apply
```

Voir aussi [`PATCH_AZERTY.md`](PATCH_AZERTY.md) (InputManager + DLL SecCams).

## Encodage (critique)

ZFBrowser lit ces HTML en **Windows-1252**, pas en UTF-8.

- Sources repo (`work/p0/html/*.html`) : UTF-8 + `<meta charset="windows-1252">`
- À l’injection, `patch_browser_assets_fr.py` **ré-encode en cp1252**
- Sans ça : mojibake du type `ContrÃ´les` au lieu de `Contrôles`

## Netteté / « 480p »

Le panneau How to Play est une **vue ZFBrowser** (~560px de large en CSS), pas du TextMeshPro native Full HD. Upscale inhérent au jeu.

Atténuation appliquée dans `Foundation.css` :

- police système **Tahoma / Segoe UI** (plus nette que Lekton Google Fonts dans CEF)
- retrait du chargement Google Fonts
- légèrement plus grand (`17px` / `32px`) + antialiasing CSS

On ne peut pas passer ce panneau en « vrai » Full HD sans patch Unity (taille de la RenderTexture / HowToPlayPanel).

## QA smoke

1. Lancer Scrutinized
2. Ouvrir le tutoriel in-game (contrôles + Report Desk)
3. Vérifier accents (`é`, `ô`…), **ZQSD** (texte + images touches), images/gifs OK
4. Si problème : `python scripts\patch_browser_assets_fr.py --restore` puis re-apply HTML + `patch_tutorial_keys_azerty.py`
