# Patch P4 — Boucle d’enquête (SQLite + textures)

État au 26/07/2026. Complète P0–P3 : le **contenu** des signalements, fiches
police, SMS, posts et historiques n’était pas dans les TMP Unity.

## Source

Le fichier `Scrutinized_Data/sharedassets4.asset.res5` (nom Unity trompeur) est
une base **SQLite 3** (~277 Mo) lue via OrmLite. Inventaire :
`source/phase4/sqlite_inventory.json`.

| Table.colonne | Lignes | Lot |
|---------------|--------|-----|
| `POI.Report` | 201 | `work/lots/p4_poi.json` |
| `PoliceReport.Description` | 53 | `work/lots/p4_police.json` |
| `Convo.Message` | 3087 | `work/lots/p4_sms.json` |
| `SocialPost.PostText` | 453 | `work/lots/p4_social.json` |
| `SearchHistory.Search` | 1460 | `work/lots/p4_search.json` |
| `ReceiptItem.Item` | 1334 | `work/lots/p4_receipt.json` |

**Ne pas traduire** dans la DB : `Gender`, `HairColor`, `EyeColor` (comparaisons /
enums — risque saves). Les valeurs restent EN (`Female`, `Brown`…).

## Libellés du papier (texture)

Les titres / champs du formulaire (`SUSPICIOUS PERSON REPORT`, `SEX:`, …) sont
**baked** dans :

- `susPersonReportBG` (527×694)
- `PoliceReportBG` (496×663)

dans `sharedassets3.assets`. Patch texture = **sans risque saves** (pixels
seulement). Script : [`scripts/patch_report_textures.py`](../scripts/patch_report_textures.py).

**Important :** le script repart **toujours du vanilla** (backup + `.resS` live),
efface des rectangles pleins, puis peint le FR. Les coordonnées police sont
calées sur l’encre vanilla (titre ~y112, SUSPECT ~182, LIEU ~222, DATE ~262,
DESCRIPTION ~302) — un premier passage avec des Y trop hauts produisait du
ghosting (`POLICE REPORT` sous le FR, fragments `LO`/`SI`).

Valeurs dynamiques `Male` / `Gray` / `Green` sur les fiches : **volontairement EN**
(colonnes DB / enums). Les **options** des dropdowns D.M.V sont aussi laissées
EN pour coller aux fiches ; seuls les libellés de champs (`Sexe:`, `Cheveux:`)
sont en FR.

## Outils

| Script | Rôle |
|--------|------|
| [`scripts/scan_sqlite_fr.py`](../scripts/scan_sqlite_fr.py) | Inventaire + SHA |
| [`scripts/patch_sqlite_fr.py`](../scripts/patch_sqlite_fr.py) | Export / apply / restore |
| [`scripts/mt_translate_lots.py`](../scripts/mt_translate_lots.py) | MT EN→FR (Google via deep-translator) |
| [`scripts/patch_report_textures.py`](../scripts/patch_report_textures.py) | Libellés FR sur les BG papier |
| [`scripts/vanilla.py`](../scripts/vanilla.py) | Inclut désormais `sharedassets4.asset.res5` |

## Apply

```powershell
python scripts\vanilla.py --init   # une fois (copie la SQLite vanilla)
python scripts\patch_unity_text.py --apply
python scripts\patch_font_atlas.py --apply    # APRES le texte (fichiers partages)
python scripts\patch_sqlite_fr.py --apply
python scripts\patch_report_textures.py --apply
```

`patch_unity_text` ne doit **pas** restaurer la SQLite ni `sharedassets0`
(atlas) : ils sont listés dans `FOREIGN`. Les textures papier se réappliquent
après les atlas car elles réécrivent seulement deux `Texture2D` dans
`sharedassets3`.

## Copie runtime

Le jeu peut créer `PlayerScrut.dbase` (référencé dans la DLL) sous
`%USERPROFILE%\AppData\LocalLow\Reflect Studios\Scrutinized\`. Si les rapports
restent en anglais après patch, **supprimer cette copie** pour forcer la
relecture de `sharedassets4.asset.res5`.

**Piège vu le 26/07/2026 :** les lots JSON étaient bien en FR, mais le fichier
install `sharedassets4.asset.res5` était repassé en EN (Steam verify, restore,
ou apply pendant que le jeu tournait). Symptôme : signalements / SMS / social
encore anglais. Remède : fermer le jeu, puis
`python scripts\patch_sqlite_fr.py --apply`. Vérifier avec un SELECT sur
`POI.ID=48` (doit commencer par « Mon ex-femme… »).

## Qualité

**Relecture humaine (26/07/2026)** appliquée en jeu via `patch_sqlite_fr.py` :

| Lot | Entrées | Statut |
|-----|---------|--------|
| `p4_poi` | 201 | Main + polish (~75 `fr`) ; **re-apply 26/07/2026** |
| `p4_police` | 53 | Main + polish (~20) ; **re-apply 26/07/2026** |
| `p4_social` | 453 | Main + polish (~119) ; **re-apply 26/07/2026** |
| `p4_sms` | 3087 | Main + polish 4 tranches (~294) ; **re-apply 26/07/2026** |
| `p4_search` | 1460 | Main + polish 2 tranches ; **re-apply 26/07/2026** |
| `p4_receipt` | 1334 | Main + polish 2 tranches ; **re-apply 26/07/2026** |

Guide : [`P4_RELECTURE_STYLE.md`](P4_RELECTURE_STYLE.md) + polish [`P4_POLISH_STYLE.md`](P4_POLISH_STYLE.md). Noms / émoticônes / marques : `fr == en` OK.
Ex. SMS id 515 *Bite me* → *Va te faire foutre* ; social id 130 *put down* → *faire piquer* / *euthanasier*.

