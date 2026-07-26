# Style relecture P4 (agents)

Traduction **humaine** EN→FR des lots SQLite. **Interdit** : Google Trad / deep-translator / DeepL auto.

## Fichiers

| Lot | Chemin | Volume |
|-----|--------|--------|
| Signalements | `work/lots/p4_poi.json` | ~201 |
| Police | `work/lots/p4_police.json` | ~53 |
| Social | `work/lots/p4_social.json` | ~453 |
| SMS | `work/lots/p4_sms.json` | ~3087 |
| Search | `work/lots/p4_search.json` | ~1460 |
| Receipt | `work/lots/p4_receipt.json` | ~1334 |

Statut relecture : **poi** (201) + **police** + **social** retraduits à la main (26/07/2026) ; **SMS** lot entier (tranches **0–771**, **772–1543**, **1544–2315**, **2316–3086**) retraduit à la main (26/07/2026) ; **receipt** lot entier (tranches **0–666**, **667–1333**) retraduit à la main (26/07/2026) ; **Search** lot entier (tranches **0–729**, **730–1459**) retraduit à la main puis polish requêtes Google FR (26/07/2026). Polish qualité social : 119 `fr` (26/07/2026) — voir `P4_POLISH_STYLE.md`.

Polish qualité (`P4_POLISH_STYLE.md`) : **poi** lot entier (201, ~75 `fr`, 26/07/2026) — oral signalement citoyen ; **receipt** lot entier — tranche **0–666** (89 `fr`) + **667–1333** (78 `fr`, 26/07/2026) — générique FR / marques EN ; **SMS** tranches **0–771** (~62 `fr`) + **772–1543** (~110 `fr`) + **1544–2315** (~50 `fr`) + **2316–3086** (72 `fr`, 26/07/2026) ; **Search** **0–729** + **730–1459** (110 `fr`, 26/07/2026) ; **re-apply SQLite 26/07/2026** (`patch_sqlite_fr.py --apply`).

Ne modifier que le champ `fr`. Garder `id`, `en`, structure JSON. Préserver `\r\n` et espaces de fin si présents dans `en`.

## Glossaire (extraits)

Préserver tels quels : SCRUT, B.O.L.O, RootKit, Social Spy, Debit DB, D.M.V, Luna, Tanner, Blueblood, IMEI, DOSCoin, noms propres de personnages.

- restraining order → **ordonnance de protection**
- Jurons : fidèles au ton (fuck→putain/bordel, bitch selon contexte, bite me→va te faire foutre / casse-toi, pas « mords-moi »)
- put down (animal) → euthanasier / piquer, pas « rabaisser »
- piss off → casse-toi / fous le camp, pas « en colère »

## Ton

- Signalements citoyens : oral crédible, fautes légères OK si le EN est familier ; pas de calque Google.
- Rapports de police : registre pro, passé, factuel.
- SMS : tutoiement entre proches, abréviations SMS FR naturelles (tkt, pk, mdr…) **seulement** si le EN est déjà abrégé / chatty.
- Social : posts type Facebook 2020, ton perso, accords genre corrects.
- Accents obligatoires (é, è, à, ç…).
- Vouvoiement uniquement si le EN vouvoie ou si c’est une plainte formelle adressée à l’agence.

## Ne pas traduire / laisser `fr == en`

- Noms propres, marques, émoticônes seuls (`:)`, `>:(`), emails, URLs
- Gender/Hair/Eye (pas dans ces colonnes de lot de toute façon)
- **Receipt** : traduire le descriptif générique (*Shovel* → *Pelle*) ; laisser
  les **marques** en EN ; préserver `(1x)` / quantités / unités
- **Search** : requêtes style Google — FR naturel pour les phrases ; titres /
  lieux / marques souvent EN ; typos du personnage préservés (*tuscon*)

## Qualité

Réécrire depuis `en`, ne pas « corriger un peu » le MT pourri : repartir de l’anglais.
Français courant correct. Pas de « il m'est arrivé de » calqué, pas d’accords faux.
