# Patch texte Unity FR (pipeline UnityPy)

Couvre tout le texte stocké dans les fichiers sérialisés Unity : menus, options,
pause, écrans de chargement, fins, crédits (P0), le PC in-game (P1), le récit
d'introduction et le dialogue Luna/Tanner (P2).
Les tutoriels HTML ZFBrowser ont leur propre chaîne : [`PATCH_TUTORIAL_FR.md`](PATCH_TUTORIAL_FR.md).

## Statut

| | |
|--|--|
| BuildID cible | `20456853` |
| Lots appliqués | `p0_menus` (88) + `p1_pc` (111) + `p2_story` (60) |
| Ajustements de boîtes | 48 redimensionnées, 1 police auto-réduite (voir « Débordement UI ») |
| Méthode | UnityPy + typetrees régénérés depuis les DLL Mono |
| Fichiers réécrits | 12, tous passés au round-trip sémantique |
| Contrainte de longueur | **aucune** (mais contrainte de largeur, voir plus bas) |
| Accents | **actifs** — atlas TMP étendus en 1024² avec les glyphes latin-1 |

## Pourquoi ce pipeline

Le premier patcher, [`scripts/patch_menus_fr.py`](../scripts/patch_menus_fr.py),
réécrivait les octets en place et imposait donc `len(fr) <= len(en)`. D'où
`CONTINU.`, `QUIT`, `GRAPHISM`, `Sous-titr:`. Toute tentative de dépasser cette
limite corrompait la sérialisation et faisait crasher le jeu.

UnityPy désérialise l'objet, remplace le champ et resérialise le fichier
complet : les offsets sont recalculés, la longueur devient libre. Le ciblage
passe aussi d'une recherche d'octets à une adresse `(fichier, path_id, champ)`,
ce qui supprime les faux positifs (`GAME` qui matche autre chose que le titre
d'onglet, par exemple).

**`patch_menus_fr.py` est déprécié.** Il reste dans le dépôt comme repli
historique mais ne doit plus être lancé : il partirait de l'install déjà
patchée et ses garde-fous de longueur n'ont plus de raison d'être.

## Chaîne d'outils

| Script | Rôle |
|--------|------|
| [`scripts/vanilla.py`](../scripts/vanilla.py) | Store EN d'origine (`backup/vanilla/`) + manifeste SHA-256 |
| [`scripts/verify_integrity.py`](../scripts/verify_integrity.py) | Install vs manifeste : vanilla / patché / MAJ Steam |
| [`scripts/unity_env.py`](../scripts/unity_env.py) | Chargement UnityPy + génération des typetrees |
| [`scripts/roundtrip_test.py`](../scripts/roundtrip_test.py) | Porte de validation resérialisation |
| [`scripts/dump_unity_text.py`](../scripts/dump_unity_text.py) | Inventaire EN par PathID |
| [`scripts/check_ui_fit.py`](../scripts/check_ui_fit.py) | Mesure des libellés FR contre leur boîte |
| [`scripts/text_render.py`](../scripts/text_render.py) | Repliement du FR accentué vers l'ASCII à l'écriture |
| [`scripts/build_p2_lot.py`](../scripts/build_p2_lot.py) | Génère le lot narratif P2 depuis les traductions |
| [`scripts/scan_dll_strings.py`](../scripts/scan_dll_strings.py) | Inventaire du texte enfermé dans la DLL, et détecteur de MAJ |
| [`scripts/patch_dll_fr.py`](../scripts/patch_dll_fr.py) | Patch FR de `Assembly-CSharp.dll` via dnlib |
| [`scripts/sdf_atlas.py`](../scripts/sdf_atlas.py) | Générateur SDF (étalement calibré sur `_GradientScale = 6`) |
| [`scripts/patch_font_atlas.py`](../scripts/patch_font_atlas.py) | Extension des atlas TMP : 512→1024 + accents |
| [`scripts/restore_accents_all.py`](../scripts/restore_accents_all.py) | Restaure les accents P0–P3 sous invariant de repliement |
| [`scripts/restore_accents_p0p1.py`](../scripts/restore_accents_p0p1.py) | Alias déprécié → `restore_accents_all.py` |
| [`scripts/patch_unity_text.py`](../scripts/patch_unity_text.py) | Application des lots (texte + boîtes) |

Prérequis : `pip install UnityPy TypeTreeGeneratorAPI`.

### La porte de round-trip suit la surface patchée

`roundtrip_test.py` déduit sa liste de fichiers des lots. Une liste figée aurait
continué à afficher « tout va bien » pendant que P2 commençait à écrire dans
`sharedassets5` et `sharedassets9`, jamais testés : c'est exactement ce qui s'est
produit, et la liste est désormais dérivée automatiquement.

En élargissant la couverture, cinq fichiers ont d'abord été signalés cassés :
`level0`, `level2`, `level5`, `level8`, `sharedassets5`. Fausse alerte, mais
instructive. Les builds Unity alignent le début des données sur 4096 octets ;
UnityPy les tasse (par exemple à 1872) et met le champ d'en-tête à jour. Tout le
contenu se décale, le fichier rétrécit de deux kilo-octets, et une comparaison
octet à octet crie au feu. Trois de ces fichiers étaient déjà patchés et joués
depuis P0 sans incident.

La porte ne juge donc plus sur les octets mais sur le **sens** : identités
`(path_id, type)` inchangées, tous les typetrees MonoBehaviour toujours lisibles,
tous les textes relus identiques. Le diagnostic en octets reste affiché, comme
information.

Le build joueur n'embarque quasiment aucun typetree MonoBehaviour (3 sur 214
dans `level1`). `TypeTreeGeneratorAPI` les régénère depuis les 116 DLL de
`Scrutinized_Data/Managed`, ce qui rend `m_text` lisible et modifiable.

## Utilisation

```powershell
cd C:\Users\kaoth\Projects\Scrutinized-FR

python scripts\vanilla.py --init          # une fois : fige le EN d'origine
python scripts\verify_integrity.py        # etat de l'install
python scripts\dump_unity_text.py         # inventaire EN
python scripts\check_ui_fit.py            # debordements : doit afficher 0
python scripts\patch_unity_text.py --dry-run
python scripts\patch_unity_text.py --apply
python scripts\patch_unity_text.py --verify
python scripts\patch_unity_text.py --restore   # retour EN vanilla
```

Chaque `--apply` **repart du store vanilla** et réapplique *tous* les lots de
`work/lots/`. Les patchs ne s'empilent donc jamais, et un lot retiré revient
automatiquement en anglais. C'est aussi pour ça qu'il ne faut pas utiliser
`--lot` en usage normal : appliquer un seul lot annulerait les autres.

Seuls les JSON **objets** avec `entries` / `layout` sont lus ; les fragments
temporaires (listes `_fr_*.json`, etc.) sont ignorés — à ranger hors de
`work/lots/` (ex. `work/tmp_sms_slices/`) pour ne pas polluer le dossier.

## Format des lots

`work/lots/*.json` :

```json
{
  "meta": { "name": "...", "buildid": "20456853" },
  "entries": [
    {
      "file": "Scrutinized_Data/level1",
      "path_id": 1070,
      "field": "m_text",
      "context": "TitleUI/MenuHolder/NewGameBTN",
      "en": "NEW GAME",
      "fr": "NOUVELLE PARTIE"
    }
  ],
  "layout": [
    {
      "file": "Scrutinized_Data/level1",
      "path_id": 1070,
      "width": 467,
      "why": "NOUVELLE PARTIE"
    }
  ]
}
```

- `field` accepte un chemin pointé : `m_text`, `TipDesc`,
  `m_Options.m_Options[2].m_Text`.
- `en` sert de **garde-fou** : si le texte lu dans le vanilla ne correspond
  plus, le patcher refuse d'écrire. C'est le détecteur de mise à jour Steam.
- `context` est purement documentaire (chemin de hiérarchie de scène).
- `display` désigne le composant qui *dessine* le texte, quand ce n'est pas celui
  qui le porte. Les paragraphes du récit vivent dans des ScriptableObjects sans
  géométrie ; sans cette indication, le contrôleur de débordement les ignorerait
  en silence.
- `layout` redimensionne (`width`), déplace (`x`) une boîte, ou active
  l'auto-dimensionnement TMP (`autosize_min`). Le `path_id` désigne soit le
  composant texte, soit directement un `RectTransform` ; dans les deux cas le
  patcher agit sur le `RectTransform` du même GameObject. `width` est une
  **largeur rendue** : pour un rect étiré, dont `m_SizeDelta` contient des
  marges et non une taille, la conversion est faite automatiquement.
  `autosize_min` s'écrit en revanche sur le composant texte, dans le même cycle
  lecture/écriture que la traduction — les séparer faisait écraser l'une par
  l'autre.

## Accents : actifs

`ACCENTS_AVAILABLE = True` dans [`scripts/text_render.py`](../scripts/text_render.py).
Les 11 polices du jeu ont été étendues en 1024×1024 en **conservant les glyphes
ASCII d'origine** et en n'ajoutant que les accents (générateur SDF calibré sur
`_GradientScale = 6`). Voir `scripts/patch_font_atlas.py`.

Le packeur L-shape doit placer chaque accent sur un `m_GlyphRect` distinct (sinon
plusieurs lettres partagent la même case → `é` affiché comme `«`). La table
`m_CharacterTable` est triée par code Unicode après append. Les bitmaps SDF sont
**retournés en Y** à l'écriture (buffer atlas Unity bottom-up). Ordre d'apply sur
les fichiers partagés : `patch_unity_text` puis `patch_font_atlas` puis
`patch_dll_fr`.

Les lots P0–P3 sont accentués via [`scripts/restore_accents_all.py`](../scripts/restore_accents_all.py)
(invariant `fold(nouveau) == fold(ancien)`). Relancer le script après toute
nouvelle chaîne ASCII, puis `patch_unity_text` → `patch_font_atlas` →
`patch_dll_fr`.

## Ce qui a été corrigé par rapport au patch binaire

| EN | Avant (tronqué) | Maintenant |
|----|-----------------|------------|
| NEW GAME | NOUVELLE | NOUVELLE PARTIE |
| CONTINUE | CONTINU. | CONTINUER |
| EXIT | QUIT | QUITTER |
| SETTINGS | REGLAGES | PARAMETRES |
| GRAPHICS | GRAPHISM | GRAPHISMES |
| DISPLAY | ECRAN | AFFICHAGE |
| HOW TO PLAY | MODE EMPLOI | COMMENT JOUER |
| Subtitles: | Sous-titr: | Sous-titres: |
| RESUME | Retour | REPRENDRE |
| QUIT TO MAIN MENU | MENU PRINCIPAL | RETOUR AU MENU PRINCIPAL |

## Débordement UI

La longueur d'octets n'est plus contrainte, mais la **largeur à l'écran** l'est
toujours : le retour à la ligne automatique est actif sur presque tous les
TextMeshPro du jeu. Un libellé trop large ne déborde donc pas discrètement, il
passe à la ligne et chevauche la rangée suivante — `QUITTER` rendu `QUIT` /
`TER`, ou le deux-points de `Sous-titres :` renvoyé seul en dessous.

### Ce que mesure le contrôleur

[`scripts/check_ui_fit.py`](../scripts/check_ui_fit.py) ne compare pas une
largeur à une largeur : il **met le texte en page et compte les lignes**, puis
les compare au nombre de lignes que la boîte peut afficher (hauteur utile
divisée par l'avance de ligne). Une boîte de la hauteur d'une seule ligne ne doit
jamais en demander deux. C'est le seul critère qui décrit ce qui casse
réellement à l'écran.

Le calcul reproduit trois détails du moteur TMP, chacun ayant laissé passer des
défauts avant d'être pris en compte :

- **Avances de glyphes réelles** lues dans les atlas. Lekton, Aldrich et Roboto
  sont proportionnelles : compter les caractères ne veut rien dire.
- **Gras synthétique.** `boldSpacing` vaut 7 sur tous les atlas du jeu : un
  libellé en `m_fontStyle = 1` est 7 % plus large que la mesure naïve. C'est ce
  qui avait fait passer inaperçu le repli de l'objet d'e-mail et laissé les
  boutons du menu pause tout juste trop étroits.
- **Rects étirés.** `m_SizeDelta` y contient des marges, pas une taille ; la
  largeur rendue se reconstruit en remontant la hiérarchie jusqu'au canvas.

Les métriques de police sont mises en cache dans `build/font_metrics.json`
(le balayage des 24 fichiers est lent). **À supprimer après une mise à jour
Steam.**

Deux règles décident du verdict :

- un texte doit tenir dans le nombre de lignes affichables ;
- il ne doit **jamais demander plus de lignes que l'anglais**. Un texte que le
  jeu tronquait déjà en anglais n'est pas de notre ressort, mais aggraver la
  coupure l'est.

```powershell
python scripts\check_ui_fit.py            # 0 defaut attendu
python scripts\check_ui_fit.py --propose  # entrees layout pretes a coller
python scripts\check_ui_fit.py --all      # tout, y compris ce qui passe
```

### Les quatre leviers, par ordre de préférence

1. **Élargir la boîte** quand la place existe. Les libellés concernés sont tous
   ancrés à gauche, l'élargissement pousse donc uniquement vers la droite sans
   rien déplacer d'autre.
2. **Élargir le conteneur** quand un voisin ancré à droite gêne. `MenuHolder`
   est passé de 295 à 380 pour que l'icône « supprimer la sauvegarde », ancrée
   à droite, s'écarte de `CONTINUER` — elle suit automatiquement.
3. **Réduire la police** via `autosize_min` quand la place manque vraiment.
   `CHEVEUX:` de la fiche d'identité n'a que 2 unités de marge : la boîte est
   poussée au maximum et TMP réduit le corps de 18 à ~16,8. `m_fontSizeMax` est
   figé à la taille d'origine, le texte ne peut donc que rétrécir.
4. **Reformuler** en dernier recours. L'objet de l'e-mail est devenu
   `Lumieres et disjoncteurs`, cohérent avec la barre de titre qui, elle, n'a
   pas la place d'accueillir la version longue.

### Élargir un libellé n'élargit pas son bouton

Les boutons du jeu portent une `Image` d'alpha 0 : invisible, elle sert
uniquement de cible de clic, et sa taille est celle du bouton, pas celle du
libellé. Élargir la boîte de texte sans élargir le bouton ne se voit donc pas,
mais rend la fin du libellé **inerte au clic** — `RETOUR AU MENU PRINCIPAL`
débordait de 163 unités hors de sa zone cliquable.

Les neuf boutons concernés ont vu leur `RectTransform` aligné sur leur libellé.
Trois sont plafonnés par un voisin de la même rangée (`NewGameBTN` à 345,
`ContinueBTN` à 285, `NightmareBTN` à 310) : la zone s'arrête au bord du
voisin, sinon elle lui volerait ses clics.

**Débordement menu titre (26/07/2026)** : après *Nouvelle partie*, `MenuHolder`
est remis à `anchoredPosition.x = -295` (alpha 1) pendant que `DiffHolder` est
présenté à `x = 50`. Tout glyphe au-delà de **x ≈ -10** (soit largeur texte >~285
depuis le bord du holder) chevauche `MODE:` — d'où le `TIE` / `PAR` fantômes.
`CAUCHEMAR` trop large depuis `DiffHolder` à `-360` faisait de même le `R` sur le
menu principal. Correctif : `NewGame` **285** + `autosize_min` 28 ; `Nightmare`
**310** (vanilla) + `autosize_min` 36.

Règle : après tout élargissement de texte, vérifier que le parent portant le
`m_RaycastTarget` suit.

### Paragraphes

Les descriptions B.O.L.O et les corps d'e-mails ne défilent pas : leur dernière
ligne est coupée en deux si le texte dépasse. Trois d'entre eux ont été
resserrés pour tenir intégralement, ce que la version anglaise ne faisait
d'ailleurs pas. Les descriptions de difficulté (`TipDesc`) et les options de
listes déroulantes sont mesurées contre leur boîte d'affichage réelle
(`TipText` 450×160, `m_ItemText` / `m_CaptionText` du `Dropdown`) et tiennent
sans intervention.

### Convention deux-points

Les libellés se terminant par un deux-points s'écrivent **sans espace avant**
(`Sensibilite:`, `SEXE:`), contrairement à l'usage typographique français. Les
boîtes ont été dimensionnées pour `Label:` en anglais, et l'espace coûtait à lui
seul une dizaine d'unités — assez pour renvoyer le deux-points à la ligne sur la
moitié du panneau d'options et sur la fiche d'identité.

L'espace insécable U+00A0 est bien présent dans les atlas (`160` fait partie du
`characterSequence`) et empêcherait le renvoi à la ligne, mais il ne réduit pas
la largeur : il ne résout donc pas le problème. La règle pourra être revue lors
de la phase police, en même temps que les accents.

Dans le corps des textes en revanche, l'espace avant deux-points est conservé
(`La securite prime : laissez vos lumieres allumees`) : ces paragraphes se
replient librement.

## Périmètre couvert

**P0** (`work/lots/p0_menus.json`) : menu titre, sélection de difficulté et
descriptions `TitleTipData`, panneau options complet des deux menus (titre et
pause), écran Steam absent, écran de chargement, invites « passer la cintro »,
titres de crédits, écrans de fin.

**P1** (`work/lots/p1_pc.json`) : bureau SCRUT, e-mails, B.O.L.O, formulaires
et en-têtes de résultats des bases (D.M.V, SIM, Debit, Police Records, Social
Spy), RootKit, boutique d'améliorations, prefabs téléphone / rapport / pièce
d'identité, infobulles de la barre supérieure, pensées de Luna.

**P2** (`work/lots/p2_story.json`) : les 19 paragraphes du récit d'introduction
(`SubText` sur les objets `IST*` de `sharedassets5.assets`) et les 41 répliques du
dialogue Luna/Tanner (`DisplayText` sur les objets `LES*`/`TES*` de
`sharedassets9.assets`).

Ce lot est **généré**, pas écrit à la main :
[`scripts/build_p2_lot.py`](../scripts/build_p2_lot.py) prend le français dans
`work/p2_translations.json`, indexé par les étiquettes narratives du jeu, et
reprend `path_id`, `field` et surtout le garde-fou anglais depuis l'inventaire. Un
garde-fou recopié à la main est un garde-fou qui pourrit sans qu'on le sache. Le
script échoue si une étiquette n'a pas de traduction ou si une traduction ne
correspond à aucune cible du vanilla.

Choix de traduction, actés avec le commanditaire : **vouvoiement mutuel** entre
Luna et Tanner (la distance colle au ton maîtrisé du ravisseur), récit au **passé
simple + imparfait**, et **jurons rendus fidèlement**. Le surnom `Blueblood` reste
en anglais, conformément au glossaire et au lot P0 qui écrit déjà « le tueur
Blueblood ».

Volontairement **non traduits** :

- Noms d'apps du glossaire : RootKit, Social Spy, SIM DB, Debit DB, D.M.V DB,
  Report Desk, Records, SecCams, B.O.L.O, DOSCoin.
- `resources.assets` : ses 100 chaînes sont intégralement l'overlay de débogage
  de Unity (`DebugUI Foldout`, `New Text`, feuilles de style TMP, noms de sprites
  emoji). Rien n'y est visible par le joueur.
- `DisplayName` du dialogue : ne contient jamais que « Luna » ou « Tanner ». À
  noter que les répliques `TES1` à `TES9` n'en ont **pas** — Tanner parle avant
  que Luna ne sache qui il est. Ce vide est intentionnel, ne pas le combler.
- `SubtitleObject/SubtitleText` : placeholder « Test Mc » laissé dans un prefab.
- Sigles techniques : FXAA, TAA, SMAA, SSAA, VSync, Ultra.
- Données de remplissage des prefabs (`David Parker`, `175 lbs`, `Lorem
  ipsum`, dates factices) : écrasées à l'exécution, les traduire n'aurait
  aucun effet visible.
- L'overlay de debug `[Graphy]` dans `level3`.

## Reste à faire

- **Accents de P0 et P1** : écrits en ASCII avant l'existence du repliement,
  donc à retraduire lors de la phase police.
- **Texte enfermé dans `Assembly-CSharp.dll`** : 35 chaînes visibles par le
  joueur, dont les messages des applis de recherche et les deux écrans de fin.
  Inventaire, difficultés et options dans
  [`LIMITES_CONNUES.md`](LIMITES_CONNUES.md).
- **Prompts d'interaction maison** : cherchés dans les assets **et** dans les
  littéraux de la DLL, introuvables dans les deux. Ils n'existent probablement pas
  sous forme de texte.

## Police et accents

Les atlas TextMeshPro du jeu sont générés avec
`characterSequence = "32 - 126, 160, 8203, 8230, 9633"`, c'est-à-dire **ASCII
imprimable uniquement**. C'est vérifiable directement dans les objets
`Aldrich-Regular SDF`, `Lekton-Bold SDF` et `SpecialElite-Regular SDF` de
`sharedassets1.assets`.

Conséquence : un `é` ou un `à` n'existe pas dans l'atlas, TMP bascule sur une
police de secours et le rendu mélange deux typographies. D'où le repliement
décrit plus haut.

La chaîne de repli a été tracée précisément, parce qu'elle conditionne la phase
police. Aucune police du jeu n'a de table de repli propre, et la liste globale de
`TMP_Settings` est vide ; le recours final est donc `m_defaultFontAsset`, soit
`LiberationSans SDF` de `resources.assets`, qui pointe lui-même vers
`LiberationSans SDF - Fallback`. Or **cette dernière est en mode atlas dynamique**
(`m_AtlasPopulationMode = 1`) : elle sait rasteriser n'importe quel glyphe à
l'exécution. C'est pour cela que les accents s'affichent au lieu de laisser un
blanc, et pourquoi ils s'affichent dans la mauvaise police.

L'espoir était de basculer `Lekton`, `Aldrich` et `Roboto` dans ce mode pour que
TMP produise lui-même les glyphes accentués, dans la bonne typographie.
**Vérification faite, c'est impossible** : `m_SourceFontFile` est vide pour les
quatorze polices du jeu, Unity retirant le TTF des polices en mode statique. Sans
fichier source, pas de rastérisation dynamique. Les deux chemins qui restent, et
leurs coûts respectifs, sont dans
[`LIMITES_CONNUES.md`](LIMITES_CONNUES.md).

Les polices utilisées par les textes déjà traduits : `Aldrich-Regular SDF`,
`Lekton-Regular SDF` et `SDF2`, `Lekton-Bold SDF`, `Roboto-Regular/Bold/Black
SDF`, `COUR SDF`, `COURBD SDF`, `SpecialElite-Regular SDF`, `typewcond_*` et
`digital-7 SDF`. Ces deux dernières n'ont même pas les points de suspension.

Les pages ZFBrowser ne sont pas concernées : autre moteur de rendu, accents
Windows-1252 déjà en place.

## Sécurité et rollback

`backup/vanilla/` contient les 24 fichiers sérialisés EN d'origine (223 Mo),
avec `work/vanilla_manifest.json` qui en donne les SHA-256. `verify_integrity.py`
compare l'install au manifeste et sort en code d'erreur si le rollback est
compromis ou si le BuildID Steam a changé.

Chaque `--apply` dépose aussi un backup horodaté de l'état précédent dans
`backup/unity/`.

## Historique : le crash du 2026-07-25

`Player.log` :

> A scripted object (probably TitleTipData?) has a different serialization
> layout when loading. (Read 152 bytes but expected 156 bytes) → Crash!!!

Le patcher binaire écrivait les chaînes Unity avec un NUL terminateur et un
padding `align4(len + 1)`, ce qui décalait le champ suivant quand la longueur
était déjà multiple de 4. Le format réel est `int32 length` + UTF-8 **sans**
NUL + padding `align4(length)`.

La leçon reste valable même avec UnityPy : ne jamais supposer le format
sérialisé, et toujours valider par un round-trip sans modification avant de
toucher au contenu. C'est ce que fait `roundtrip_test.py`.
