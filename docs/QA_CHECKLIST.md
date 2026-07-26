# Checklist QA in-game (Scrutinized)

Unity 2019.4 + ZFBrowser. BuildID cible : voir `docs/PHASE0_FINDINGS.md`.

**Dernière passe visuelle menus/PC : 25/07/2026 (P0–P1).** P4 (SQLite + textures
papier) appliqué le **26/07/2026** — QA in-game boucle enquête encore à cocher
ci-dessous. Accents TMP actifs (plus de repliement ASCII).

## Porte de validation (avant toute QA de contenu)

À rejouer après chaque changement de pipeline ou mise à jour Steam.

- [ ] `python scripts\verify_integrity.py` sort en code 0
- [ ] `python scripts\roundtrip_test.py` : les 12 fichiers patchés en `OK`. La
      liste est déduite des lots, donc elle s'élargit toute seule quand un lot
      touche un nouveau fichier. Un « en-tête retassée » n'est pas une anomalie :
      le verdict porte sur les identités d'objets, la lisibilité des typetrees et
      les textes relus, pas sur les octets
- [ ] `python scripts\roundtrip_test.py --install` puis le jeu démarre **en
      anglais** : menu, options, une nuit se lance, le PC s'ouvre
- [ ] `python scripts\check_ui_fit.py` annonce `0 defauts visibles (CASSE)`
- [ ] `python scripts\patch_unity_text.py --verify` après application des lots

Si le round-trip casse quoi que ce soit : ne pas forcer, revenir au patch
binaire et documenter.

## Système

- [ ] Menu titre : NOUVELLE PARTIE / CONTINUER / PARAMETRES / COMMENT JOUER / QUITTER
- [ ] Libellés à deux-points sans espace avant (`Sensibilite:`), volontaire
- [ ] Sélection de difficulté : DETENTE / DETECTIVE / NORMAL / CAUCHEMAR + descriptions
- [ ] Options (titre et pause) : JEU / AFFICHAGE / GRAPHISMES et leurs libellés
- [ ] Menus déroulants : Patate / Basse / Moyenne / Elevee / Ultra, Aucun, Illimite
- [ ] Pause : REPRENDRE / PARAMETRES / RETOUR AU MENU PRINCIPAL / QUITTER LE JEU
- [ ] Écran de chargement : CHARGEMENT + astuce jump scares
- [ ] Tutoriel HTML ZFBrowser en FR (accents cp1252) — libellés **ZQSD**
- [ ] Images touches tuto : **Z/Q/S/D** (plus WASD)
- [ ] Déplacement maison **ZQSD** (AZERTY forcé — voir `PATCH_AZERTY.md`)
- [ ] Lampe **F** ; skip intro **S** ; crédits **Q** ; SecCams **Q/D** (+ flèches)
- [ ] Crédits : titres de sections FR, noms propres inchangés
- [ ] Fins : « Encore une nuit de passee », « A suivre... »
- [ ] Aucun injecteur BepInEx / MelonLoader / Harmony actif pendant la QA
- [ ] Accents UI lisibles (menus, options, pause) — pas de glyphe parasite



## Débordement UI

`check_ui_fit.py` garantit qu'aucun texte ne demande plus de lignes que sa boîte
n'en affiche, ni plus que la version anglaise. Ce qu'il ne sait pas voir, et qui
se contrôle donc à l'œil : une boîte élargie qui recouvre un élément voisin, et
tout ce qui est mis en page à l'exécution (groupes de disposition, fenêtres
instanciées). 48 boîtes ont été redimensionnées, à vérifier en priorité :

- [ ] Menu titre : `NOUVELLE PARTIE` / `CONTINUER` / `QUITTER` sur une seule ligne
      (NewGame **285** + autosize min 28 — limite géométrie Diff à x=50)
- [ ] Pas de `R` fantôme à gauche du menu (CAUCHEMAR 310 + autosize min 36)
- [ ] Après **Nouvelle partie** : `MODE:` sans chevauchement `TIE` / `PAR` / `PARTIE`
- [ ] Menu titre avec une sauvegarde existante : l'icône corbeille ne touche
      pas `CONTINUER` (`MenuHolder` élargi de 295 à 380)
- [ ] Difficulté : `RETOUR` / `DETENTE` / `CAUCHEMAR` sans chevauchement
- [ ] Options : le deux-points reste sur la même ligne que son libellé
- [ ] Pause : `REPRENDRE` / `RETOUR AU MENU PRINCIPAL` / `QUITTER LE JEU`
- [ ] **Clic sur la fin des libellés** de boutons (menu titre, difficulté,
      pause) : le survol et le clic répondent aussi sur les derniers caractères,
      pas seulement au début du mot
- [ ] Intro : `Appuie sur [S] pour passer` — les trois éléments alignés, la
      touche ni collée ni superposée au texte (positions décalées)
- [ ] Crédits : `SCENARISTES PRINCIPAUX`, `ARTISTES PERSONNAGES`
- [ ] Boutique : bouton `ACHETER` (bouton élargi de 100 à 120, vers la gauche)
- [ ] Téléphone : `RETOUR` ne déborde pas de son en-tête
- [ ] Fiche d'identité : libellés `CHEVEUX:` / `TAILLE:` sans chevauchement des
      valeurs de la colonne de droite. `CHEVEUX:` est le seul libellé à police
      auto-réduite (18 → ~16,8) : vérifier que l'écart de taille avec ses
      voisins reste imperceptible
- [ ] Social Spy : onglet vertical `PUBLICATIONS` contenu dans l'onglet
- [ ] E-mail : la ligne `Objet:` tient sur une seule ligne, sans que le bas des
      lettres soit rogné par la limite de l'en-tête
- [ ] B.O.L.O ravisseur et Tanner : la dernière ligne du paragraphe est entière,
      pas coupée en deux par le bord de la fenêtre (ces fenêtres ne défilent pas)
- [ ] Corps des deux e-mails : dernière ligne entière, signature visible



## Gameplay

- [ ] Prompts maison (ouvrir / fermer / allumer / éteindre / fenêtres / se cacher)
- [ ] Bureau SCRUT : icônes, titres de fenêtres, infobulles de la barre du haut
- [ ] E-mails : objet, De/A, corps des deux messages
- [ ] B.O.L.O : descriptions ravisseur et Tanner
- [ ] Bases de données : formulaires, boutons, en-têtes de résultats
- [ ] RootKit : CRACKER / CRACK INSTANT / CONNEXION
- [ ] Boutique d'améliorations : titres et bouton ACHETER
- [ ] Téléphone : PHOTOS / SMS / RECHERCHES / RETOUR
- [ ] Rapports : PREUVES, PIECE D'IDENTITE, libellés de la fiche
- [ ] Décisions **Menace** / **Pas une menace**
- [ ] Pensées de Luna (démarrage, coupure internet, disjoncteur)



## Récit et dialogue (P2)

Le récit d'introduction se mesure : il s'affiche dans une boîte de 1720 × 150,
soit 5 lignes à la taille 26. Le dialogue, lui, est dessiné par un prefab
redimensionné à l'exécution — aucune mesure statique n'est possible, d'où les
contrôles à l'œil ci-dessous.

- [ ] Nouvelle partie : les 19 paragraphes du récit défilent en français, chacun
      entier, aucune ligne coupée en bas de la boîte
- [ ] `IST14` (le paragraphe sur les demandes d'accès refusées) : c'était le seul
      à déborder, resserré pour tenir en 5 lignes — vérifier qu'il tient
- [ ] Dialogue Tanner : les répliques tiennent dans la boîte de sous-titres sans
      rognage ni chevauchement du nom du locuteur
- [ ] `TES1` à `TES9` s'affichent **sans nom de locuteur** : c'est voulu, Luna ne
      sait pas encore qui parle
- [ ] Vouvoiement cohérent dans les deux sens sur toute la scène
- [ ] Accents lisibles dans le récit / dialogue (pas de glyphe « 6 » ni « « »)

## DLL et dates (P3)

- [ ] Messages des applis de recherche FR (« Aucun résultat… », etc.)
- [ ] Écrans de fin FR : kidnapping / statistique
- [ ] Titre des nuits FR : `NUIT UNE`, `NUIT DEUX`, … (plus `NUIT ONE`)
- [ ] Dates / horloge en 24 heures
- [ ] `python scripts\scan_dll_strings.py` code 0

## Boucle d’enquête (P4)

Détail : [`PATCH_ENQUETE_FR.md`](PATCH_ENQUETE_FR.md).

- [ ] Signalement citoyen : titre/libellés FR sur le papier + corps du rapport FR
      (ex. Amelie Linter / ordonnance de protection)
- [ ] Fiche police : `RAPPORT DE POLICE` + description FR
- [ ] SMS téléphone et posts Social Spy en français
- [ ] Historique de recherches / tickets Debit en français (marques OK en EN)
- [ ] Si rapports encore EN : supprimer
      `%USERPROFILE%\AppData\LocalLow\Reflect Studios\Scrutinized\PlayerScrut.dbase`
      s’il existe
- [ ] Couleurs / sexe EN partout de façon cohérente : fiches **et** dropdowns
      D.M.V (`Gray`, `Male`…) ; libellés de champs toujours FR (`Cheveux:`)
- [ ] `python scripts\scan_sqlite_fr.py` : inventaire cohérent
- [ ] Save/load smoke après patch texture papier

## Limites documentées

Détail : [`LIMITES_CONNUES.md`](LIMITES_CONNUES.md).

- [ ] Valeurs de fiche volontairement EN : `Male`, `Brown`, `Blonde`, ` lbs`
- [ ] **Vérifier l’hypothèse** prompts d’interaction textuels maison
- [x] Relecture humaine `p4_police.json` (53 entrées)
- [x] Polish P4 police lot entier (`P4_POLISH_STYLE.md`, 20 retouches / 53) — 26/07/2026
- [x] Relecture humaine P4 social (453 posts)
- [x] Polish qualité P4 social (~9/10, 119 `fr`) + re-apply SQLite 26/07/2026
- [x] Relecture humaine P4 SMS index 0–771 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS index **0–771** (`P4_POLISH_STYLE.md`, ~62 retouches) — 26/07/2026
- [x] Relecture humaine P4 SMS index 772–1543 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS index **772–1543** (`P4_POLISH_STYLE.md`, ~110 retouches) — 26/07/2026
- [x] Relecture humaine P4 SMS index 1544–2315 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS index **1544–2315** (`P4_POLISH_STYLE.md`, ~50 retouches) — 26/07/2026
- [x] Relecture humaine P4 SMS index 2316–3086 (`p4_sms.json`) — 26/07/2026
- [x] Polish P4 SMS index **2316–3086** (`P4_POLISH_STYLE.md`, 72 retouches) — 26/07/2026
- [x] Relecture humaine `p4_poi.json` (201 signalements) — 26/07/2026
- [x] Polish P4 `p4_poi.json` lot entier (`P4_POLISH_STYLE.md`, ~75 retouches) — 26/07/2026
- [x] Relecture humaine P4 search index **0–729** (`p4_search.json`) — 26/07/2026
- [x] Polish P4 search index **0–729** (`p4_search.json`) — 26/07/2026 (requêtes Google FR)
- [x] Relecture humaine P4 search reste (**730–1459**) — 26/07/2026
- [x] Polish P4 search index **730–1459** (`P4_POLISH_STYLE.md`, 110 retouches) — 26/07/2026
- [x] Relecture humaine P4 : receipt lot entier (0–666 + 667–1333, 26/07/2026)
- [x] Polish P4 receipt index **0–666** (`P4_POLISH_STYLE.md`, 89 retouches) — 26/07/2026
- [x] Polish P4 receipt index **667–1333** (`P4_POLISH_STYLE.md`, 78 retouches) — 26/07/2026

## Rollback

- [ ] `python scripts\patch_unity_text.py --restore` remet le jeu en anglais
- [ ] `python scripts\patch_sqlite_fr.py --restore` remet la DB enquête EN
- [ ] Textures papier : restaurer `sharedassets3.assets` depuis le store vanilla
      (`backup/vanilla/`) puis rejouer `patch_unity_text` + `patch_font_atlas` si besoin
- [ ] Le jeu vanilla démarre correctement après restauration
- [ ] `python scripts\verify_integrity.py` ne signale plus que `browser_assets`