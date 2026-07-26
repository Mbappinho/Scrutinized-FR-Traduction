# Phase 0 — Findings (Scrutinized)

> Rempli le 2026-07-25. Build inspecté : install Steam locale.

## Identité jeu

| Champ | Valeur |
|-------|--------|
| Titre | Scrutinized |
| Studio | Reflect Studios |
| Steam AppID | `1384770` |
| BuildID | **`20456853`** |
| Chemin install | `C:\Steam\steamapps\common\Scrutinized` (via `local_game_path.txt`) |
| Exe shipping | `Scrutinized.exe` + `UnityPlayer.dll` |
| Data | `Scrutinized_Data\` |
| PersistentData | `%USERPROFILE%\AppData\LocalLow\Reflect Studios\Scrutinized\` (logs uniquement) |

## Moteur / archives

| Champ | Valeur |
|-------|--------|
| Moteur | **Unity 2019.4.7f1** (lu dans `globalgamemanagers`) |
| Scripting | **Mono** (`Managed\`, pas de `il2cpp_data`) |
| Assemblies jeu | `Assembly-CSharp.dll` (~613 KB), `Assembly-CSharp-firstpass.dll` |
| Format Unreal | **Absent** — pas de `Content\Paks`, pas de IoStore |
| Browser in-game | **ZFBrowser** (`ZFBrowser.dll` + CEF sous `Plugins\`) |
| Resource browser | `Scrutinized_Data\Resources\browser_assets` (~117 MB, magic `zfbRes_v1`) |
| Assets Unity | `resources.assets`, `sharedassets0–9.assets`, `level0–9`, `globalgamemanagers*` |
| StreamingAssets | **Absent** |
| `.sig` Unreal | N/A |

### Conséquence pipeline

Le kit initial inspiré de WTTG3 (Unreal / locres / retoc / UAssetGUI / pak `_P`) est **invalide** pour Scrutinized. Réutiliser seulement : glossaire Reflect, discipline BuildID, QA, workflow lots.

## Localisation native

| Élément | Présent ? | Notes |
|---------|-----------|-------|
| `Game.locres` Unreal | Non | N/A |
| Unity Localization package (plein) | Module moteur seulement | `UnityEngine.LocalizationModule.dll` présent ; pas de preuves d’un catalogue FR/EN prêt |
| I2 Localization | Non | Pas de DLL I2 |
| TextAsset / UI / TMP dans `.assets` | Oui | Narration Luna / crédits / « HOW TO PLAY » / options détectés en ASCII dans assets |
| FStrings Unreal | Non | N/A |
| HTML ZFBrowser | **Oui** | `Tutorial.html`, `TutorialControls.html`, `Foundation.css` en **clair** après EOCD ZIP interne |
| Sites / images tutoriel | Oui | ~49 chemins `Tutorial/*.png` (icônes apps SCRUT) |
| Textures baked | Possible | À vérifier Phase 1 (crédits / intros) |
| SQLite gameplay | **Oui** | `sharedassets4.asset.res5` = SQLite 3 (OrmLite). Voir [`PATCH_ENQUETE_FR.md`](PATCH_ENQUETE_FR.md) |

### Inventaire chiffré (scripts)

| Source | Résultat |
|--------|----------|
| `scripts/extract_browser_assets.py` | 2 HTML + 1 CSS extraits ; **~169** chaînes UI tutoriel |
| `scripts/phase0_inventory.py` (assets mid-size) | **482** chaînes playerish ; **91** « interesting » |
| `Assembly-CSharp.dll` | Beaucoup d’**identifiants** code (reports, doors, Kidnapper, Tanner…) — peu de libellés UI littéraux évidents |
| AssetStudio CLI TextAsset JSON | `Dialogs`, `Errors`, `Keyboard`, `Cursors` (+ line breaking TMP) — HTML ZFBrowser chrome / clavier |
| Gros assets TMP UI | Dump CLI peu fiable → **GUI AssetStudio** recommandée |

### Correction Phase 1 : le PC in-game n'est pas du HTML

L'hypothèse de départ — « le gros du PC sim est dans `browser_assets` » — est
**fausse**. Le ZIP imbriqué dans `browser_assets` ne contient que le tutoriel :
44 PNG, 6 GIF, 1 CSS, 1 HTML. Les apps SCRUT (Report Desk, D.M.V DB, Social
Spy, SIM DB, Debit DB, RootKit, Upgrades, téléphone, rapports) sont de l'UI
Unity / TextMeshPro dans `level3` et `sharedassets3.assets`.

L'ordre de priorité a donc été inversé : UI Unity d'abord, HTML ensuite.

### Inventaire réel par PathID

L'inventaire ASCII heuristique de `phase0_inventory.py` /
`scan_unity_ui_strings.py` est remplacé par
[`scripts/dump_unity_text.py`](../scripts/dump_unity_text.py), qui lit les
objets via des typetrees régénérés. Résultat :
`source/phase1/tmp_text_inventory.json`, **547 chaînes** dont 379 uniques.

| Fichier | Chaînes | Contenu |
|---------|---------|---------|
| `level3` | 166 | PC in-game + menu pause |
| `sharedassets3.assets` | 78 | Prefabs PC, améliorations, pensées de Luna |
| `sharedassets9.assets` | 75 | **Sous-titres de dialogue** (`DisplayText`) |
| `level1` | 42 | Menu titre et options |
| `level7` | 46 | Crédits |
| `sharedassets5.assets` | 19 | **Intro narrative** (`SubText`) |
| `resources.assets` | 100 | Assets TMP par défaut, non joueur |
| autres | 21 | level0/2/5/8/9, `TitleTipData` de `sharedassets1` |

Découvertes notables : les descriptions de difficulté vivent dans des
ScriptableObjects `TitleTipData` (`TipTitle` / `TipDesc`), et les dialogues et
l'intro n'avaient jamais été repérés jusque-là.

### Lots appliqués

- Tutos FR : `browser_assets` — [`PATCH_TUTORIAL_FR.md`](PATCH_TUTORIAL_FR.md)
- P0 menus / options / pause / crédits / fins : 88 textes
- P1 PC in-game : 111 textes
- Pipeline et périmètre : [`PATCH_MENUS_FR.md`](PATCH_MENUS_FR.md)

## Prochaine étape

1. QA visuelle du débordement UI (les libellés ne sont plus tronqués)
2. **P2** : sous-titres `sharedassets9` + intro `sharedassets5`
3. Phase police : régénérer les atlas TMP en latin-1, puis réintroduire les accents
4. Prompts d'interaction maison : toujours introuvables dans les assets

## Apps / marques découvertes (preserve)

Préfixe UI bureau **SCRUT** + apps tutoriel :

- **Report Desk** (Shredder / Report / Fax)
- **D.M.V. DB**
- **Social Spy**
- **Debit DB**
- **SIM DB**
- **RootKit**
- **Records**
- **SecCams**
- **Upgrades**
- Toolbar : Bonus Report, **DOS Coin**, Date, Early Bed, Incorrect Report, Insta Crack Key, Network, Report Quota, Time

Personnages / voix crédits (assets) : Luna (Sarah Thomas), Tanner (Michael Malconian), Kidnapper (Johnlp76).

## Stratégie retenue

- [x] **Mixte (priorité ci-dessous)**
- [ ] Locres Unreal → Non applicable
- [ ] Patch FString UAssetGUI → Non applicable

### Ordre d’implémentation (révisé après Phase 1)

1. **UI Unity / TMP** (`level*`, `sharedassets*`) via UnityPy + typetrees — le
   gros du texte joueur, menus **et** PC in-game
2. **HTML/CSS ZFBrowser** (`browser_assets`) — le tutoriel, et rien d'autre
3. **Littéraux `Assembly-CSharp.dll`** — valeurs remplies à l'exécution et
   prompts maison ; dernier recours, non traité

## Outils validés

| Outil | Version / chemin | OK ? |
|-------|------------------|------|
| Scripts repo `extract_browser_assets.py` | `scripts/` | Oui — extract plaintext web |
| Scripts repo `phase0_inventory.py` | `scripts/` | Oui — scan ASCII + DLL |
| `game_paths.py` | `scripts/` | Oui |
| Scripts repo `scan_unity_ui_strings.py` / `patch_menus_fr.py` | `scripts/` | **Dépréciés** — remplacés par le pipeline UnityPy |
| Scripts repo `vanilla.py` / `verify_integrity.py` | `scripts/` | Oui — store EN + intégrité |
| Scripts repo `dump_unity_text.py` / `patch_unity_text.py` | `scripts/` | Oui — inventaire + patch par PathID |
| Scripts repo `roundtrip_test.py` | `scripts/` | Oui — porte de validation, validée in-game |
| UnityPy | 1.25 (pip) | **Oui** — y compris `sharedassets3.assets` (36 Mo) |
| TypeTreeGeneratorAPI | 0.0.10 (pip) | Oui — indispensable, 3 typetrees embarqués sur 214 |
| AssetStudio | `tools/AssetStudio/` v2.4.1 (Razviar, net8) | **Oui** — GUI + CLI |
| ILSpy / dnSpy | À placer sous `tools/` | Lecture Mono |
| retoc / UAssetGUI / UnrealLocres / UE4SS | WTTG3 | **Hors scope** |

## Risques repérés

- **Mauvais pipeline Unreal** si un agent reprend l’ancien handoff sans lire ce fichier.
- **`browser_assets` format hybride** : index `zfbRes_v1` + ZIP (EOCD ~ offset 61519125) + **HTML/CSS en clair** après l’EOCD. Repack = reconstruire ce conteneur, pas un simple drop de fichiers.
- **Ne pas traduire** chemins `Tutorial/*.png`, `foundation.css` / `base.css`, noms de fichiers apps.
- **Typos EN upstream** (ex. « Flaslight ») — corriger en FR sans calquer la faute.
- **Overflow UI** HTML/CSS fixed-width possible.
- **Gros assets** non dumpés en Phase 0 — inventaire menus incomplets jusqu’à AssetStudio.
- **SQLite** : contenu de la boucle d’enquête dans
  `sharedassets4.asset.res5` (pas un `.db` séparé). Patch P4 :
  [`PATCH_ENQUETE_FR.md`](PATCH_ENQUETE_FR.md).
- **CEF `Plugins\locales\*.pak`** = locales Chrome, **pas** la loc jeu.
- **MAJ Steam** : re-vérifier BuildID `20456853` ; rebuild depuis le même cook.

## Ton

Tutoiement / vouvoiement **selon le contexte** (décision joueur / glossaire) :

- UI maison / prompts / tutoriel contrôles → plutôt **tutoiement** (immédiat, survival)
- Rapports / ton pro A.D.O.S / fax → plutôt **vouvoiement** ou neutre administratif

## Scripts de reproduction

```text
python scripts/extract_browser_assets.py
python scripts/phase0_inventory.py
python scripts/scan_unity_ui_strings.py
python scripts/patch_browser_assets_fr.py --apply
python scripts/patch_menus_fr.py --apply
```
