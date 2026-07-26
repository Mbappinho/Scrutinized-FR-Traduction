# Kit de transfert agent — Scrutinized FR

> Export initial inspiré de l’expérience **WTTG3-FR-Loc** (Reflect Studios).  
> Référence méthodologique : `C:\Users\kaoth\Projects\WTTG3-FR-Loc`  
> Cible de ce dépôt : **Scrutinized** (Steam AppID `1384770`).

Ce document est destiné à un **nouvel agent** qui démarre ou reprend la localisation FR dans **ce** repo.

---

## 1. Contexte studio / jeux

| | WTTG3 (référence méthodo) | Scrutinized (cible) |
|--|--|--|
| Studio | Reflect Studios | Reflect Studios |
| Steam AppID | `3869850` | `1384770` |
| Sortie | 2025–2026 | 2020 |
| Moteur | Unreal **5.6.1**, IoStore | **Unity 2019.4.7f1**, Mono |
| Protagoniste | Simon Zhao | Luna Youngman |
| Ton | Horreur / darknet / PC sim | Horreur psy / analyste criminel / PC sim / maison |
| Browser in-game | (UE / raw files) | **ZFBrowser** (`Resources\browser_assets`) |

Les deux jeux partagent : UI PC simulé, dossiers / preuves, apps maison, tension nocturne.  
Les noms d’apps WTTG3 (CryptChat, VirtMesh, DarkDrop…) **ne s’appliquent pas** à Scrutinized — sauf termes studio vraiment partagés (ex. **A.D.O.S**).

### Règle critique

**Ne pas** copier le pipeline Unreal WTTG3 (retoc, UAssetGUI, locres, pak `_P`, UE4SS). Scrutinized n’a **pas** de `Content\Paks`.

---

## 2. Règle d’or (cook / build)

Un patch qui override des fichiers du jeu doit être buildé depuis **exactement le même build Steam** que le joueur.

| Situation | Résultat typique |
|-----------|------------------|
| Pack FR buildé depuis l’install Steam cible, même BuildID | OK |
| Pack FR buildé depuis une autre copie / autre build | Textes EN, UI cassée, ou crash |
| MAJ Steam qui remplace assets / `browser_assets` / DLL | Ancien pack peut casser → re-extract + rebuild |

Documenter dès le début :

- AppID + **BuildID** (`steamapps/appmanifest_1384770.acf`)
- Chemin d’install (`local_game_path.txt`)
- Version Unity (ex. `2019.4.7f1` dans `globalgamemanagers`)
- Sources texte : `.assets` Unity, `browser_assets` ZFBrowser, littéraux `Assembly-CSharp.dll`

BuildID Phase 0 documenté : **`20456853`**.

---

## 3. Phase 0 — Découverte (faite / à maintenir)

Voir [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md).

### 3.1 Inventaire fichiers (Unity)

Dans `<Game>\Scrutinized_Data\` :

1. Lister `*.assets`, `level*`, `resources.assets`, `globalgamemanagers*`
2. Noter `Managed\` (Mono) vs absence de `il2cpp_data`
3. Examiner `Resources\browser_assets` (ZFBrowser `zfbRes_v1`)
4. Chercher bases SQLite embarquées vs runtime (`persistentDataPath`) —
   **trouvées** : `sharedassets4.asset.res5` (ship) + évent. `PlayerScrut.dbase`

### 3.2 Stratégie retenue (ordre)

**Correction importante par rapport à l'hypothèse initiale :** le PC in-game
n'est **pas** en HTML. Le `BrowserAssets.zip` imbriqué ne contient que le
tutoriel (44 PNG, 6 GIF, 1 CSS, 1 HTML). Les apps SCRUT sont de l'UI Unity /
TextMeshPro dans `level3` et `sharedassets3.assets`.

| Priorité | Cible | Statut |
|----------|--------|--------|
| 1 | UI Unity / TMP dans `level*` et `sharedassets*` | P0, P1 et P2 faits |
| 2 | HTML/CSS dans `browser_assets` | Tutoriel fait, rien d'autre dedans |
| 3 | Littéraux `Assembly-CSharp.dll` (Mono) | P3 fait (35 chaînes) |
| 4 | SQLite enquête + textures papier | P4 fait — [`PATCH_ENQUETE_FR.md`](PATCH_ENQUETE_FR.md) |

### 3.3 Outils

| Outil | Usage |
|-------|--------|
| **UnityPy** + **TypeTreeGeneratorAPI** | Pipeline de production, lecture/écriture des assets |
| **AssetStudio** / AssetRipper | Exploration visuelle d'appoint |
| **ILSpy** / dnSpy | Lecture seule des assemblies Mono |

Outils Unreal WTTG3 (`retoc`, `UAssetGUI`, `UnrealLocres`, `UE4SS`) : **hors scope** Scrutinized.

---

## 4. Pipeline en place

```
1. Verifier BuildID + integrite            verify_integrity.py
2. Inventaire EN par PathID                dump_unity_text.py
3. Traduire en lots JSON                   work/lots/*.json
4. Porte de validation reserialisation     roundtrip_test.py
5. Mesurer les debordements                check_ui_fit.py
6. Appliquer et controler                  patch_unity_text.py --apply --verify
7. Atlas TMP + accents                     patch_font_atlas.py --apply
8. DLL FR (+ SecCams A→Q)                  patch_dll_fr.py --apply
9. Input AZERTY (ZQSD)                     patch_input_azerty.py --apply
10. Tutoriel HTML                          patch_browser_assets_fr.py --apply
11. Images touches ZQSD                    patch_tutorial_keys_azerty.py --apply
12. SQLite enquête                         patch_sqlite_fr.py --apply
```

AZERTY : [`PATCH_AZERTY.md`](PATCH_AZERTY.md). Détail Unity texte : [`PATCH_MENUS_FR.md`](PATCH_MENUS_FR.md).

La porte de round-trip déduit sa liste de fichiers des lots. C'est important : une
liste figée continuait d'annoncer « tout va bien » pendant que P2 écrivait dans
deux fichiers jamais testés. Et son verdict porte sur le **sens** — identités
d'objets, typetrees lisibles, textes relus — pas sur les octets, parce qu'UnityPy
retasse légitimement l'en-tête que Unity alignait sur 4096 octets.

Le point non évident : le build joueur n'embarque presque aucun typetree
MonoBehaviour (3 sur 214 dans `level1`). Sans `TypeTreeGeneratorAPI`, qui les
régénère depuis les DLL de `Scrutinized_Data/Managed`, UnityPy ne sait pas lire
`m_text` et le pipeline entier ne fonctionne pas.

Le texte ne vit pas que dans `m_text` : `TipTitle` / `TipDesc`
(`TitleTipData`), `Tip`, `Title`, `toolTipMessage`, `DisplayText` /
`DisplayName` (dialogues), `SubText` (intro), et les options de menus
déroulants dans `m_Options.m_Options[N].m_Text`.

### Encodage

- UI Unity / TMP : les atlas SDF du jeu sont générés sur le charset
  `32 - 126` — **ASCII imprimable uniquement**. Tout accent bascule sur une
  police de secours et se voit.
- Les lots stockent malgré tout le **français accentué** ; `scripts/text_render.py`
  replie vers l'ASCII à l'écriture. Écrire directement en ASCII, comme l'ont fait
  P0 et P1, détruit la traduction et obligera à la refaire. Tout script qui a
  besoin de savoir ce que le joueur verra doit passer par `rendered()` — le
  contrôleur de débordement compris, sinon il mesure des largeurs fausses.
- Écrire les **apostrophes droites** et les points de suspension en trois points :
  `’` n'existe dans aucun atlas du jeu, même en anglais.
- HTML ZFBrowser : **Windows-1252** (pas UTF-8 — mojibake sinon) ; voir `PATCH_TUTORIAL_FR.md`.
- **Ne jamais** traduire chemins (`*.html`, `*.css`, `*.js`, `*.png`, URLs relatives).

### Textes sans boîte à eux

Le récit d'introduction et le dialogue vivent dans des ScriptableObjects, sans
géométrie. Un contrôleur de débordement qui ne regarde que l'objet porteur les
ignore **en silence**, ce qui est le pire des cas. D'où le champ `display` dans les
lots, qui désigne le composant qui dessine réellement le texte : le récit est
mesuré contre `level5#94`, 1720 × 150, cinq lignes. Le dialogue, lui, passe par un
prefab redimensionné à l'exécution et reste hors de portée de la mesure.

Quand on ajoute une cible de ce genre, vérifier que le contrôleur la voit vraiment
en sabotant volontairement une traduction : s'il ne dit rien, c'est lui qui est
cassé, pas la traduction qui est bonne.

### Overflow UI

La longueur d'octets n'est plus contrainte, mais la largeur à l'écran l'est. Le
retour à la ligne automatique étant actif sur presque tous les TextMeshPro, un
libellé trop large chevauche la rangée suivante au lieu de déborder discrètement.

`check_ui_fit.py` met le texte en page avec les avances de glyphes des atlas TMP,
**compte les lignes** et les compare à ce que la boîte affiche. Il doit annoncer
`0 defauts visibles (CASSE)`. Quand ça déborde, le réflexe est d'**élargir la
boîte** via la section `layout` du lot (les libellés sont ancrés à gauche,
l'élargissement ne déplace rien), puis `autosize_min`, et seulement en dernier
recours de raccourcir la traduction.

Trois pièges de modélisation, tous découverts après coup en jeu :

- le **gras synthétique** ajoute 7 % d'avance (`boldSpacing`) ; l'ignorer rend
  toute mesure de libellé en gras optimiste, donc les élargissements trop justes ;
- une comparaison largeur contre largeur ne décrit rien : ce qui casse est le
  **nombre de lignes** ;
- « déjà limité en anglais » n'est pas un laissez-passer. La règle retenue est de
  ne jamais demander **plus de lignes que l'anglais**.

Et un piège de patch : les boutons portent une `Image` d'alpha 0 servant de cible
de clic. Élargir le texte sans élargir le bouton ne se voit pas mais rend la fin
du libellé inerte. Toujours faire suivre le parent qui porte le
`m_RaycastTarget`.

Deux conventions qui en découlent : les libellés à deux-points s'écrivent sans
espace avant (`Sensibilite:`), et le contrôle visuel d'un recouvrement entre une
boîte élargie et son voisin reste manuel. Détail :
[`PATCH_MENUS_FR.md`](PATCH_MENUS_FR.md), section « Débordement UI ».

---

## 5. Pièges à anticiper

- Confondre CEF `Plugins\locales\*.pak` (Chrome) avec de la loc jeu — **ignorer**.
- `browser_assets` format propriétaire ZFBrowser (`zfbRes_v1`) — extract/repack dédié.
- SQLite / OrmLite : données peuvent être générées à runtime ; ne pas assumer un `.db` dans l’install.
- MAJ Steam : re-vérifier BuildID + hash des fichiers overridés.
- WTTG3 : crashes « cook Unreal » — ici plutôt assets Unity corrompus / HTML cassé / DLL mismatch.

---

## 6. Workflow traduction

1. Inventaire EN (CSV/JSON) depuis Phase 0 / re-extract.
2. Glossaire (`work/glossary.json`) avant gros lots.
3. **P0** : menus, pause, prompts maison, tutos HTML.
4. **P1** : apps PC / rapports / preuves / décisions Menace.
5. **P2** : récit d'introduction et dialogue Luna/Tanner.
6. QA in-game ([`QA_CHECKLIST.md`](QA_CHECKLIST.md)).
7. Release avec BuildID + notes maj.

### Qualité

- Français correct et **accentué dans les lots** ; le repliement ASCII est
  l'affaire du patcher, pas du traducteur.
- Pas de Google Trad brut.
- Ton : voir glossaire. Le jeu **tutoie le joueur** dans l'UI, mais Luna et Tanner
  se **vouvoient** dans le dialogue — la distance sert le personnage du ravisseur.
- Récit d'introduction au **passé simple + imparfait**, registre littéraire noir.
- Jurons rendus fidèlement, pas édulcorés.
- Préserver placeholders et noms (A.D.O.S, Luna, Tanner, Adam, Blueblood…).

### Maintenance post-MAJ Steam

```
1. Lire nouveau BuildID
2. Re-extract assets + browser_assets
3. Diff inventaire EN
4. Remapper clés cassées
5. Rebuild pack + bump BuildID documenté
```

---

## 7. Glossaire

Fichier : [`../work/glossary.json`](../work/glossary.json)

- `preserve` : ne pas traduire
- `preferred` : choix FR stables
- `tone` / `rules` : contraintes rédactionnelles

---

## 8. Checklist démarrage Scrutinized

- [x] Install Steam + BuildID `appmanifest_1384770.acf`
- [x] Confirmer moteur Unity (pas Unreal)
- [x] Confirmer Mono + `Managed\Assembly-CSharp.dll`
- [x] Confirmer ZFBrowser `browser_assets`
- [x] Extraire inventaire strings EN (Phase 0 : browser HTML + assets mid-size + DLL ; gros assets → AssetStudio)
- [x] Choisir stratégie (HTML ZFB → assets → DLL)
- [x] AssetStudio installé : `tools/AssetStudio/` (v2.4.1 net8)
- [x] Créer `local_game_path.txt`
- [x] Étendre glossaire (apps SCRUT + ton contextuel)
- [x] Lot P0 tutos HTML FR + patch `browser_assets` (voir `docs/PATCH_TUTORIAL_FR.md`)
- [x] Store vanilla EN + manifeste SHA-256 (`backup/vanilla/`, `work/vanilla_manifest.json`)
- [x] Pipeline UnityPy + typetrees, porte de round-trip validée in-game
- [x] Inventaire exhaustif par PathID (`source/phase1/tmp_text_inventory.json`)
- [x] Lot P0 menus / options / pause / crédits / fins (88 textes, sans troncature)
- [x] Lot P1 PC in-game : bureau SCRUT, e-mails, B.O.L.O, bases, prefabs (111 textes)
- [x] Débordement UI mesuré et corrigé : 48 boîtes élargies (dont 9 zones
      cliquables), 1 police auto-réduite, 4 textes resserrés, `check_ui_fit.py` à 0
- [x] QA visuelle des débordements : aucun constaté en jeu sur le menu titre, les
      options, le menu pause et le PC (25/07/2026)
- [x] Fix débordement menu titre : `NOUVELLE PARTIE` / `CAUCHEMAR` re-cadrés dans
      les holders + autosize (plus de `R` / `PAR` fantômes) — 26/07/2026
- [x] **AZERTY** : InputManager ZQSD + SecCams A→Q + tutos HTML/PNG — 26/07/2026
      (voir [`PATCH_AZERTY.md`](PATCH_AZERTY.md))
- [x] Lot P2 narratif : 19 paragraphes du récit d'introduction et 41 répliques du
      dialogue Luna/Tanner (60 textes), vouvoiement mutuel, passé simple
- [x] Repliement d'accents à l'écriture (`scripts/text_render.py`) : les lots
      peuvent enfin stocker du vrai français
- [x] Porte de round-trip élargie aux 12 fichiers patchés, verdict sémantique
- [x] Lot P3 DLL : 35 chaînes de `Assembly-CSharp.dll` (dnlib + pythonnet)
- [x] Atlas TMP étendus en 1024² avec accents (11 polices) ; `ACCENTS_AVAILABLE`
- [x] Accents P0/P1 restaurés sous invariant (40 libellés) + 2 boîtes réajustées
- [x] Fix packeur atlas (rects uniques + table caractères triée) — re-apply fonts
- [x] Fix orientation Y des glyphes injectés (flip bottom-up) + bearingY capitales
- [x] Passe accents complète P0–P3 (`restore_accents_all.py`) + re-apply patches
- [x] P4 boucle enquête : SQLite (POI/police/SMS/social/search/receipt) + textures papier
- [ ] QA visuelle : accents, messages SCRUT FR, dates 24h, écrans de fin FR,
      signalements / SMS / posts FR, et clic sur la fin des libellés
- [ ] Couleurs de cheveux/yeux (énumérations) : toujours en anglais, hors périmètre
      tant qu'on n'intercepte pas l'affichage
- [x] Relecture humaine `p4_police.json` (53 descriptions PV, registre pro)
- [x] Polish P4 `p4_police.json` (53, registre PV ; 20 retouches) — 26/07/2026
- [x] Relecture humaine P4 social (`p4_social.json`, 453) — 26/07/2026
- [x] Polish qualité P4 social (~9/10, 119 `fr`) — 26/07/2026
- [x] Relecture humaine P4 SMS tranche index 0–771 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS tranche index **0–771** (~62 retouches) — 26/07/2026
- [x] Relecture humaine P4 SMS tranche index 772–1543 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS tranche index **772–1543** (~110 retouches) — 26/07/2026
- [x] Relecture humaine P4 SMS tranche index 1544–2315 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS tranche index **1544–2315** (~50 retouches) — 26/07/2026
- [x] Relecture humaine P4 SMS tranche index 2316–3086 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS tranche index **2316–3086** (72 retouches) — 26/07/2026
- [x] Relecture humaine `p4_poi.json` (201 signalements citoyens) — 26/07/2026
- [x] Polish P4 `p4_poi.json` (201, oral citoyen ; ~75 retouches) — 26/07/2026
- [x] Relecture humaine P4 search tranche index **0–729** (`p4_search.json`) — 26/07/2026
- [x] Polish P4 search tranche index **0–729** (`p4_search.json`) — 26/07/2026 (requêtes Google FR naturelles)
- [x] Relecture humaine P4 search reste (**730–1459**) — 26/07/2026
- [x] Polish P4 search tranche index **730–1459** (`p4_search.json`, 110 retouches) — 26/07/2026
- [x] Relecture humaine P4 : receipt lot entier (**0–666**, **667–1333**) (26/07/2026)
- [x] Polish P4 receipt **0–666** (89 retouches) (26/07/2026)
- [x] Polish P4 receipt **667–1333** (78 retouches) (26/07/2026)
- [x] **Re-apply SQLite polish P4** (`patch_sqlite_fr.py --apply`) — 26/07/2026 ; spot-check `POI.ID=48` FR

---

## 9. Fichiers utiles

| Fichier | Pourquoi |
|---------|----------|
| `docs/PHASE0_FINDINGS.md` | Vérité terrain moteur / sources / stratégie |
| `docs/LIMITES_CONNUES.md` | Ce qui reste en anglais et pourquoi — à lire avant de chercher un texte |
| `docs/PATCH_ENQUETE_FR.md` | Pipeline P4 SQLite + textures papier |
| `docs/INSTALL.md` | Install joueur (Release zip) |
| `docs/PATCH_AZERTY.md` | AZERTY ZQSD |
| `release/steam_target.json` | BuildID / version pack |
| Pack joueur | [Releases](https://github.com/Mbappinho/Scrutinized-FR-Traduction/releases) |
| `docs/QA_CHECKLIST.md` | QA in-game |
| `work/glossary.json` | Glossaire |
| `scripts/` | Extract / inventaire Phase 0 |
| WTTG3 `work/glossary.json` | Style Reflect seulement — ne pas importer les apps |

Ne versionne pas : extracts `source/`, `tools/` binaires, `build/`, chemins perso.

---

## 10. Ce que ce kit n’est pas

- Pas une copie du pipeline Unreal WTTG3.
- Pas une traduction Scrutinized déjà faite.
- Pas une garantie que tout le texte est dans le HTML ZFBrowser (vérifier assets + DLL).

**Première action utile :** QA in-game P4 (tous les lots SQLite relus à la main
et appliqués) ; ne pas toucher enums couleurs.
