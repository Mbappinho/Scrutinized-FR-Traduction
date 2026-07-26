# -*- coding: utf-8 -*-
"""
Paint French labels onto susPersonReportBG / PoliceReportBG and inject
back into sharedassets3.assets. Saves-safe (texture only).

Always starts from the **vanilla** texture (via backup + live .resS), so
re-applies are idempotent and do not stack ghosts.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from game_paths import ROOT, data_dir
from unity_env import close_env, load_env
from vanilla import vanilla_path

ASSETS = "sharedassets3.assets"
FONT = ROOT / "tools" / "fonts" / "SpecialElite-Regular.ttf"
OUT_DIR = ROOT / "build" / "report_textures"

# Coordinates measured from vanilla Texture2D ink (PoliceReportBG / susPersonReportBG).
SUS_LABELS = [
    ("SIGNALEMENT PERSONNE SUSPECTE", 95, 28, 15),
    ("SUSPECT:", 18, 82, 14),
    ("DATE:", 18, 118, 14),
    ("SEXE:", 18, 157, 13),
    ("TAILLE:", 175, 157, 13),
    ("CHEVEUX:", 330, 157, 13),
    ("ÂGE:", 18, 190, 13),
    ("POIDS:", 175, 190, 13),
    ("YEUX:", 330, 190, 13),
    ("RAPPORT", 18, 225, 14),
]

POLICE_LABELS = [
    ("RAPPORT DE POLICE", 125, 112, 17),
    ("SUSPECT:", 18, 182, 14),
    ("LIEU:", 18, 222, 14),
    ("DATE:", 18, 262, 14),
    ("DESCRIPTION", 18, 302, 14),
]

SUS_ERASE = [
    (90, 22, 430, 48),  # title
    (12, 78, 110, 98),  # SUSPECT
    (12, 114, 80, 138),  # DATE
    (12, 152, 420, 175),  # SEX HEIGHT HAIR
    (12, 185, 420, 210),  # AGE WEIGHT EYES
    (12, 220, 100, 245),  # REPORT
]

# Vanilla ink: title ~109-134; SUSPECT ~181-193; LOCATION ~221-233;
# DATE ~261-273; DESCRIPTION ~301-313.
POLICE_ERASE = [
    (100, 105, 390, 140),  # POLICE REPORT
    (12, 175, 120, 200),  # SUSPECT
    (12, 215, 140, 240),  # LOCATION
    (12, 255, 100, 280),  # DATE
    (12, 295, 160, 320),  # DESCRIPTION
]


def paper_fill(arr: np.ndarray, box: tuple[int, int, int, int]) -> None:
    """Replace the whole rectangle with local paper color (no selective ink)."""
    x0, y0, x1, y1 = box
    h, w = arr.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    # Sample paper from a band above the box (avoid ink).
    sy0 = max(0, y0 - 25)
    sy1 = max(sy0 + 1, y0)
    sample = arr[sy0:sy1, x0:x1]
    if sample.size:
        sl = sample[..., :3].mean(axis=2)
        light = sample[sl > 200]
    else:
        light = np.empty((0, 4), dtype=np.uint8)
    if len(light) < 10:
        color = np.array([232, 230, 226, 255], dtype=np.uint8)
    else:
        color = np.median(light, axis=0).astype(np.uint8)
    arr[y0:y1, x0:x1] = color


def erase_and_paint(
    base: Image.Image,
    erase_boxes: list[tuple[int, int, int, int]],
    labels: list[tuple[str, int, int, int]],
) -> Image.Image:
    arr = np.array(base.convert("RGBA"))
    for box in erase_boxes:
        paper_fill(arr, box)
    out = Image.fromarray(arr)
    draw = ImageDraw.Draw(out)
    for text, x, y, size in labels:
        font = ImageFont.truetype(str(FONT), size)
        draw.text((x, y), text, font=font, fill=(20, 20, 20, 255))
    return out


def find_tex(env, name: str):
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        t = o.read()
        if getattr(t, "m_Name", None) == name:
            return o, t
    return None, None


def load_vanilla_image(name: str) -> Image.Image:
    """Decode Texture2D from vanilla assets + live .resS sidecars."""
    van = vanilla_path(f"Scrutinized_Data/{ASSETS}")
    resS = data_dir() / f"{ASSETS}.resS"
    if not van.is_file():
        raise SystemExit(f"Vanilla manquant: {van}")
    if not resS.is_file():
        raise SystemExit(f"resS manquant: {resS}")
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy2(van, tmp / ASSETS)
        shutil.copy2(resS, tmp / f"{ASSETS}.resS")
        env = load_env(tmp / ASSETS)
        try:
            _, tex = find_tex(env, name)
            if tex is None:
                raise SystemExit(f"{name} introuvable dans vanilla")
            return tex.image.copy()
        finally:
            close_env(env)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def patch_one(live_env, name: str, labels, erase_boxes, dry: bool) -> None:
    base = load_vanilla_image(name)
    painted = erase_and_paint(base, erase_boxes, labels)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    preview = OUT_DIR / f"{name}_FR.png"
    painted.save(preview)
    print(f"Preview {preview} {painted.size}")
    if dry:
        return
    obj, tex = find_tex(live_env, name)
    if tex is None:
        raise SystemExit(f"{name} introuvable dans l'install")
    tex.set_image(painted)
    tex.save()
    print(f"  texture {name} mise a jour en memoire")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run or not args.apply

    assets = data_dir() / ASSETS
    env = None if dry else load_env(assets)
    try:
        if dry:
            # Still build previews from vanilla without touching install.
            for name, labels, boxes in (
                ("susPersonReportBG", SUS_LABELS, SUS_ERASE),
                ("PoliceReportBG", POLICE_LABELS, POLICE_ERASE),
            ):
                base = load_vanilla_image(name)
                painted = erase_and_paint(base, boxes, labels)
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                painted.save(OUT_DIR / f"{name}_FR.png")
                print(f"Preview {OUT_DIR / f'{name}_FR.png'} {painted.size}")
        else:
            patch_one(env, "susPersonReportBG", SUS_LABELS, SUS_ERASE, dry)
            patch_one(env, "PoliceReportBG", POLICE_LABELS, POLICE_ERASE, dry)
            assets.write_bytes(env.file.save())
            print(f"Ecrit {assets}")
    finally:
        if env is not None:
            close_env(env)
    if dry:
        print("Dry-run OK — verifier build/report_textures/*_FR.png puis --apply")


if __name__ == "__main__":
    main()
