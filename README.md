# Scrutinized — Traduction française

Fan patch de localisation française **non officiel** pour *Scrutinized* (Reflect Studios).

<a href='https://ko-fi.com/T1P023QR7T' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi2.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

> **Joueur / débutant :** télécharge le pack prêt à l’emploi dans  
> [Releases](https://github.com/Mbappinho/Scrutinized-FR-Traduction/releases)  
> (`Scrutinized-FR-Traduction.zip` → `INSTALLER.bat` / `DESINSTALLER.bat`).

Ce dépôt contient le **code source du pipeline** (scripts, lots, docs), **pas** le jeu.

## Compatibilité Steam

| | |
|--|--|
| **Pack actuel** | **v1.0.0** |
| **Steam AppID** | `1384770` |
| **BuildID** | `20456853` |
| Vérifier | `steamapps/appmanifest_1384770.acf` → `"buildid"` |

`INSTALLER.bat` détecte ton BuildID et prévient en cas d’écart.

## Installation (débutant)

1. Ferme Scrutinized.
2. Télécharge le zip de la [dernière Release](https://github.com/Mbappinho/Scrutinized-FR-Traduction/releases).
3. Dézippe n’importe où.
4. Double-clique **`INSTALLER.bat`**, choisis le dossier du jeu, confirme avec **O**.
5. Relance le jeu.

Pour retirer la trad : **`DESINSTALLER.bat`** (restaure le backup anglais créé à l’install).  
Sinon : Steam → Propriétés → Fichiers installés → Vérifier l’intégrité.

### Contenu FR

- Menus / options / pause / tutoriel HTML
- PC in-game (SCRUT), récit, dialogue Luna/Tanner
- Boucle enquête (signalements, SMS, social, recherches, reçus…)
- Accents TMP, dates 24 h, **clavier AZERTY (ZQSD)**
- Textures papier signalement / rapport police

Enums volontairement EN : `Male`, `Brown`, `Unknown`, etc. (saves).

## Après une MAJ Steam

1. Vérifie l’intégrité Steam (repart EN).
2. Installe une **release FR** rebuildée pour le **nouveau BuildID**.
3. Un vieux pack peut faire crasher ou laisser de l’anglais.

## Développeurs

```powershell
python -m pip install -r requirements.txt
# chemin jeu dans local_game_path.txt
python scripts\vanilla.py --init
# puis chaîne d'apply — voir docs/AGENT_HANDOFF.md et docs/PATCH_AZERTY.md
powershell -File scripts\build_beginner_pack.ps1
```

| Doc | Sujet |
|-----|--------|
| [`docs/INSTALL.md`](docs/INSTALL.md) | Install joueur |
| [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md) | Pipeline agent |
| [`docs/PATCH_AZERTY.md`](docs/PATCH_AZERTY.md) | AZERTY |
| [`docs/LIMITES_CONNUES.md`](docs/LIMITES_CONNUES.md) | Limites |
| [`docs/QA_CHECKLIST.md`](docs/QA_CHECKLIST.md) | QA |

Référence méthode : [WTTG3-FR-Traduction](https://github.com/Mbappinho/WTTG3-FR-Traduction) (même studio, moteur différent).
