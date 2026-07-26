# Patch AZERTY (ZQSD)

Scrutinized est câblé **QWERTY**. Le pack FR **force AZERTY** : positions
physiques de déplacement = ancien WASD → libellés **ZQSD**.

Clavier QWERTY physique : non supporté par ce pack (documenté).

## Remap

| Entrée | Vanilla | FR AZERTY |
|--------|---------|-----------|
| `Horizontal` alt− | `a` | `q` |
| `Horizontal` alt+ | `d` | `d` |
| `Vertical` alt+ | `w` | `z` |
| `Vertical` alt− | `s` | `s` |
| Lampe `F` | `f` | inchangé |
| Skip intro | `KeyCode.S` | inchangé |
| Crédits quit | `KeyCode.Q` | inchangé |
| SecCams gauche | `KeyCode.A` | `KeyCode.Q` |

Fichier InputManager : `Scrutinized_Data/globalgamemanagers`.

## Scripts

```powershell
cd C:\Users\kaoth\Projects\Scrutinized-FR

python scripts\patch_input_azerty.py --apply
python scripts\patch_input_azerty.py --verify
python scripts\patch_input_azerty.py --restore

# SecCams A→Q est inclus dans le patch DLL FR :
python scripts\patch_dll_fr.py --apply

# Tutos HTML ZQSD + images touches :
python scripts\patch_browser_assets_fr.py --apply
python scripts\patch_tutorial_keys_azerty.py --apply
```

`patch_tutorial_keys_azerty.py` repeint `WASDF.png` / `wasdKeys.png` dans le
pool zfbRes de `browser_assets` (pad à la taille d’origine). À lancer **après**
le patch HTML, sur le fichier live.

## Ordre d’apply complet (rappel)

```text
patch_unity_text → patch_font_atlas → patch_dll_fr
patch_input_azerty
patch_browser_assets_fr → patch_tutorial_keys_azerty
patch_sqlite_fr
```

Chaque script **repart du vanilla** pour son fichier cible (sauf
`patch_tutorial_keys_azerty`, qui patche le `browser_assets` déjà FR).

## QA

- Déplacement maison **ZQSD**, courir (Shift), s’accroupir (Ctrl)
- Lampe **F**
- Skip intro **S** / Escape
- Crédits **Q**
- SecCams : **Q/D** (+ flèches / Space)
- Menu Comment jouer : texte + images **ZQSD**

## Hors scope

- Clavier virtuel HTML ZFBrowser (chrome CEF)
- Axe orphelin `TakeUse` / `e` (interact = souris)
