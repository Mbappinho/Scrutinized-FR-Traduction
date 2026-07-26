# -*- coding: utf-8 -*-
"""Resolve Scrutinized game root without committing personal paths."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def game_root() -> Path:
    env = os.environ.get("SCRUTINIZED_GAME", "").strip().strip('"')
    if env:
        return Path(env)
    local = ROOT / "local_game_path.txt"
    if local.exists():
        line = local.read_text(encoding="utf-8").strip().strip('"')
        if line and not line.startswith("#"):
            return Path(line)
    raise SystemExit(
        "Chemin du jeu inconnu. Cree local_game_path.txt a la racine du depot "
        "(une ligne = dossier Steam Scrutinized) "
        "ou definis SCRUTINIZED_GAME."
    )


def data_dir() -> Path:
    return game_root() / "Scrutinized_Data"


def managed_dir() -> Path:
    return data_dir() / "Managed"


def browser_assets_path() -> Path:
    return data_dir() / "Resources" / "browser_assets"
