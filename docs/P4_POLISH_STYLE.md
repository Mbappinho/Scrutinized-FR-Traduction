# Style polish P4 — passe qualité (cible ~9/10)

Objectif : **amélioration notable** des lots déjà relus. Pas de MT auto.
Repartir de `en` ; réécrire `fr` quand c’est plat, calqué ou maladroit.
Garder `fr` seulement s’il est déjà naturel et fidèle.

## Interdits / calques à corriger

| EN / problème | Éviter | Préférer |
|---------------|--------|----------|
| call X over to his car | appeler X jusqu’à sa voiture | l’appeler / le faire venir près de sa voiture |
| smashed a bottle | écrasé une bouteille (ambigu) | a smashé / a jeté / a brisé une bouteille par terre |
| over the speed limit | au-dessus de la limite | largement au-dessus de la limitation |
| it seems strange; no, | C’est peut-être… mais non, | Non, ça cloche / Ça me paraissait louche |
| live laugh love (traduit) | « live rire amour » | garder EN ou « live laugh love » |
| put down (animal) | rabaisser | euthanasier / faire piquer |
| Bite me | Mords-moi | Va te faire foutre / Casse-toi |
| piss off | en colère | casse-toi / fous le camp |
| restraining order | ordonnance de ne pas faire | ordonnance de protection |
| « il m’est arrivé de » | calque | Je suis tombé sur / J’ai croisé… |

## Ton par corpus

- **POI** : oral signalement citoyen, vivant, pas admin.
- **Police** : PV factuel, sobre, professionnel.
- **SMS** : tutoiement si EN tutoyant ; jurons fidèles ; abréviations seulement si EN abrégé.
- **Social** : post FB, accords genre, idiomes.
- **Search** : requête Google FR naturelle ; typos personnage conservés ; titres/marques souvent EN.
- **Receipt** : générique FR ; **marques EN** ; `(1x)` / quantités préservés.
  - Tranche **0–666** polie (26/07/2026, ~89 `fr`) ; **667–fin** selon checklist.

## Technique

- Modifier uniquement `fr`. Préserver `id`, `en`, `\r\n`, espaces de fin.
- JSON UTF-8 indent 2. Pas d’apply SQLite. Pas de commit.
- Noms propres / SCRUT / B.O.L.O / RootKit : inchangés.
- Accents obligatoires.

## Statut polish (26/07/2026)

**Re-apply SQLite** : `python scripts\patch_sqlite_fr.py --apply` le **26/07/2026** (tous lots polish). Spot-check : `POI.ID=48` « Mon ex-femme… », `Convo.ID=1557` « j'adore entendre ça… ».

| Lot | Plage | Statut |
|-----|-------|--------|
| `p4_search` | index **0–729** | Fait — ~222 `fr` ; **en jeu** |
| `p4_search` | index **730–1459** | Fait — 110 `fr` ; **en jeu** |
| `p4_receipt` | index **0–666** | Fait — 89 `fr` ; **en jeu** |
| `p4_receipt` | index **667–1333** | Fait — 78 `fr` ; **en jeu** |
| `p4_sms` | index **0–771** | Fait — ~62 `fr` ; **en jeu** |
| `p4_sms` | index **772–1543** | Fait — ~110 `fr` ; **en jeu** |
| `p4_sms` | index **1544–2315** | Fait — ~50 `fr` ; **en jeu** |
| `p4_sms` | index **2316–3086** | Fait — 72 `fr` ; **en jeu** |
| `p4_social` | lot entier (453) | Fait — 119 `fr` ; **en jeu** |
| `p4_poi` | lot entier (201) | Fait — ~75 `fr` ; **en jeu** |
| `p4_police` | lot entier (53) | Fait — 20 `fr` ; **en jeu** |
