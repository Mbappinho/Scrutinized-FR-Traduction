# Limites connues — ce qui restera en anglais, et pourquoi

État au 26/07/2026, lots P0 + P1 + P2 appliqués. À reprendre après toute mise à
jour Steam.

Ce document existe pour éviter deux pertes de temps symétriques : chercher un
texte qui n'existe pas, et croire intraduisible quelque chose qui ne l'est pas.
Chaque limite ci-dessous est le résultat d'une vérification, pas d'une supposition,
et la commande qui la rejoue est indiquée.

## Les assets sont terminés

Sur les 547 textes de `source/phase1/tmp_text_inventory.json`, 259 sont traduits.
Les 288 autres sont des exclusions décidées, pas des oublis :

| Combien | Quoi | Pourquoi |
|---------|------|----------|
| 100 | `resources.assets` | Overlay de débogage de Unity (`DebugUI Foldout`, `New Text`, feuilles de style TMP, noms de sprites emoji). Jamais affiché. |
| 34 | `DisplayName` du dialogue | Ne contient que « Luna » ou « Tanner ». |
| 32 | Noms du générique (`level7`) | Noms propres. |
| 22 | `[Graphy]` dans `level3` | Overlay de télémétrie du développeur. |
| ~30 | Gabarits `Option A` des menus déroulants | Écrasés à l'exécution par les vraies options, déjà traduites. |
| ~40 | Données de remplissage des prefabs | `David Parker`, `Male`, `175 lbs`, `Lorem ipsum`, `Test`, dates factices. Écrasées à l'exécution. |
| le reste | Noms d'apps et sigles | `RootKit`, `Social Spy`, `B.O.L.O`, `SIM DB`, `FXAA`, `Ultra`… Voir `preserve` dans le glossaire. |

Deux libellés sont absents des lots pour une raison plus subtile : `NORMAL` et
`DETECTIVE` s'écrivent identiquement en français **une fois les accents repliés**.
Après la phase police, `DETECTIVE` devra devenir `DÉTECTIVE`.

Vérification : `python scripts\dump_unity_text.py` puis comparaison avec
`work/lots/*.json`.

## Le texte enfermé dans Assembly-CSharp.dll

**Statut : patché** via [`scripts/patch_dll_fr.py`](../scripts/patch_dll_fr.py)
(lot `work/lots/p3_dll.json`, 35 chaînes). Fautes d'origine corrigées, dates en
24 h français (`dd/MM/yyyy HH:mm`), genre accordé pour Luna. L'unité reste ` lb`
(le jeu est américain ; convertir en kg sans convertir les chiffres serait faux).

Inventaire toujours suivi par `python scripts\scan_dll_strings.py` (lit le
**vanilla**, pas l'install patchée).

Ce qui est concerné, par ordre de visibilité :

- **Les messages des applis de recherche**, qui reviennent en boucle dans la
  boucle de jeu : « No results found. », « No police record found. », « No recent
  transactions found. », « This person does not have a social profile. »,
  « Please specify at least one search parameter. », les trois messages IMEI, et
  les fautes d'origine « Invaid Search. Name is to short. » qu'il faudra décider de
  reproduire ou de corriger.
- **Les deux écrans de fin** : « You Have Been Kidnapped. », « You Became A
  Statistic. »
- **Les rejets de quota** : « Report Quota Not Met. », « Too Many Reports
  Rejected. », « WRONG! »
- **Le titre des nuits**, composé à l'exécution (`NIGHT ` + mot-nombre). Les
  deux parties sont patchées (`NUIT ` + `UNE`…`QUATORZE` via `GameDataSlinger`).
- **Deux pensées de Luna** : patchées (`Je devrais me reposer…`, etc.).
- **Les valeurs de fiche** `Male` / `Female` / couleurs : **volontairement EN**
  (enums). Unité ` lb`.
- **Les formats de date** : patchés en 24 h (`dd/MM/yyyy HH:mm`).

### Pourquoi c'est difficile, et les deux façons de s'y prendre

Réécrire un littéral demande de reconstruire l'assembly. Deux modèles, et le choix
n'est pas technique mais éditorial :

1. **Réécriture statique** avec `dnlib` ou `Mono.Cecil` : la bibliothèque
   reconstruit le tas de chaînes, donc aucune contrainte de longueur. Le patch
   reste un simple remplacement de fichier, cohérent avec le reste du projet, mais
   il faut un SDK .NET et la DLL devra être repatchée à chaque mise à jour Steam.
2. **Greffon BepInEx** avec des correctifs Harmony : non destructif, survit mieux
   aux mises à jour, mais impose au joueur d'installer un injecteur. Le projet s'en
   est passé jusqu'ici, et la checklist QA demande même qu'aucun injecteur ne
   tourne pendant les tests.

### Les couleurs de cheveux et d'yeux sont un cas à part

`Brown`, `Blonde`, `Hazel`, `Blue`, `Bald`, `Green`, `Red` ne sont **pas** des
littéraux : ils n'existent que dans le tas de métadonnées, ce qui est la signature
de **noms de membres d'énumération**. Le code possède bien des propriétés
`HairColor` et `EyeColor`, et affiche donc la couleur en transformant une
énumération en texte.

Renommer un membre d'énumération ne renomme pas seulement ce que le joueur lit :
cela change aussi ce que voit tout aller-retour texte, toute clé de dictionnaire et
tout contenu de sauvegarde qui passerait par là. Avant d'y toucher, il faut lire le
code à l'ILSpy pour savoir si la chaîne sert uniquement à l'affichage. La bonne
solution est probablement de ne pas y toucher du tout et d'intercepter l'affichage.

## Boucle d’enquête (P4)

**Statut : patché** — corps des signalements / fiches / SMS / posts / recherches /
tickets Debit via SQLite (`sharedassets4.asset.res5`), libellés papier via
textures `susPersonReportBG` / `PoliceReportBG`. Détail :
[`PATCH_ENQUETE_FR.md`](PATCH_ENQUETE_FR.md).

Toujours en anglais **volontairement** sur les fiches **et** dans les
dropdowns D.M.V (`Male` / `Female` / `Gray` / `Brown`…) : ce sont les mêmes
valeurs d’enums / colonnes DB. Traduire seulement les listes créait un écart
pénible (chercher « Gris » alors que la fiche affiche `Gray`). Les libellés de
champs restent FR (`Sexe:`, `Cheveux:`, `Yeux:`).

Si le jeu a créé `PlayerScrut.dbase` sous LocalLow, le supprimer pour voir le FR.

## Les accents

**Statut : actifs.** Les atlas TMP sont étendus en 1024² (ASCII vanilla conservé +
accents append) via `scripts/patch_font_atlas.py`. Les lots écrivent du français
accentué (`ACCENTS_AVAILABLE = True`).

**Piège déjà rencontré (packeur L-shape).** Une première version de
`pack_into_free` réutilisait les mêmes `m_GlyphRect` pour plusieurs accents
(ex. `é` et `«` en `(517,5)`), d'où l'affichage `Sensibilit«` / `R«solution` en
jeu. Correctif : packing bande droite puis bas avec refus de collision, et tri de
`m_CharacterTable` par `m_Unicode` (TMP cherche en dichotomie).

**Piège Y de l'atlas.** Le buffer Alpha8 sérialisé est **bottom-up** (un `A`
vanilla apparaît à l'envers si on traite l'octet 0 comme le haut). Les bitmaps
PIL sont top-down : il faut les **retourner verticalement** à l'injection, sinon
les accents s'affichent sous la lettre (sorte de « 6 » / crochet). Les bearings
capitales ne doivent pas se fier à `PIL.getbbox` (É donnait bearingY=12).

Après un `patch_unity_text.py` sur un fichier partagé, **rejouer**
`patch_font_atlas.py --apply` sinon les atlas retombent au vanilla.

**Mode atlas dynamique : mort.** Aucune police du jeu ne garde
`m_SourceFontFile` ; sans TTF embarqué, pas de rastérisation à l'exécution.

Limites restantes côté glyphes : `æ`/`œ` absents de certaines sources
(`typewcond_*`, parfois Special Elite) — le patcher les saute. Les pages
ZFBrowser ne sont pas concernées (autre moteur, accents déjà OK).

Côté lots : `python scripts\restore_accents_all.py` ré-injecte les accents sous
invariant de repliement, puis rejouer la chaîne d'apply. Beaucoup de libellés
courts n'ont **légitimement** aucun accent (`QUITTER`, `Volume`, `Nom:`).

## Ce qui n'existe pas

Les **prompts d'interaction** de la maison (ouvrir, fermer, allumer une lampe, se
cacher) ont été cherchés dans les deux sources et ne s'y trouvent pas : ni parmi
les 547 textes de l'inventaire, ni parmi les 512 littéraux de la DLL, où
`OpenDoor` et `CloseWindow` ne sont que des noms de méthodes. L'hypothèse la plus
probable est qu'il n'y a pas de prompt textuel du tout — icône de touche ou rien.
À confirmer d'un coup d'œil lors d'une nuit jouée ; si un texte apparaît, c'est que
cette conclusion est fausse et qu'il faut reprendre la recherche.

## Ce qui ressemble à une limite mais n'en est pas

- **L'en-tête retassée par UnityPy.** Les builds Unity alignent le début des
  données sur 4096 octets, UnityPy les tasse. Le fichier rétrécit de deux
  kilo-octets et une comparaison octet à octet crie au feu. C'est légitime : le
  moteur lit l'offset dans l'en-tête. La porte de round-trip juge sur le sens.
- **Les gabarits `Option A`.** Ils ne sont pas des textes oubliés mais les lignes
  modèles des menus déroulants ; les vraies options vivent dans
  `m_Options.m_Options[N].m_Text` et sont traduites.
- **Les données de remplissage des prefabs.** `David Parker`, `Male`, `Blonde`,
  `175 lbs` visibles dans les prefabs sont écrasés à l'exécution. Les traduire
  n'aurait aucun effet — sauf pour les valeurs listées plus haut, qui viennent bien
  du code.

## Clavier : AZERTY forcé

Le pack FR **force** le déplacement en **ZQSD** (positions physiques de l’ancien
WASD) via `globalgamemanagers` + SecCams `A→Q`. Voir
[`PATCH_AZERTY.md`](PATCH_AZERTY.md).

- Un clavier **QWERTY** physique n’est **pas** supporté par ce pack.
- Skip intro **S** et crédits **Q** restent les lettres S/Q (déjà correctes en
  AZERTY).
- Hors scope : clavier virtuel HTML ZFBrowser ; axe orphelin `TakeUse`/`e`.
