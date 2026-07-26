# -*- coding: utf-8 -*-
"""
Validate the SDF generator by regenerating Aldrich's existing glyphs and
comparing them to the shipped atlas. Must pass before any accent is injected.
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "scripts")
sys.stdout.reconfigure(encoding="utf-8")

from game_paths import ROOT
from sdf_atlas import GRADIENT_SCALE, encode_sdf, render_glyph, signed_distance_field
from unity_env import close_env, load_env
from vanilla import vanilla_path
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import zoom
import math

FONT = ROOT / "tools" / "fonts" / "Aldrich-Regular.ttf"
REL = "Scrutinized_Data/sharedassets1.assets"


def load_aldrich():
    env = load_env(vanilla_path(REL))
    by_id = {o.path_id: o for o in env.objects}
    t = None
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        if "m_FaceInfo" in tt and tt.get("m_Name") == "Aldrich-Regular SDF":
            t = tt
            break
    tex = by_id[t["m_AtlasTextures"][0]["m_PathID"]].read_typetree()
    img = np.frombuffer(bytes(tex["image data"]), dtype=np.uint8).reshape(
        t["m_AtlasHeight"], t["m_AtlasWidth"]
    )
    return env, t, img


def extract_shipped(t, img, unicode_cp: int, pad: int):
    car = {c["m_Unicode"]: c for c in t["m_CharacterTable"]}
    gly = {g["m_Index"]: g for g in t["m_GlyphTable"]}
    if unicode_cp not in car:
        return None
    g = gly[car[unicode_cp]["m_GlyphIndex"]]
    r = g["m_GlyphRect"]
    if r["m_Width"] == 0:
        return g, None
    x0 = r["m_X"] - pad
    y0 = r["m_Y"] - pad
    x1 = r["m_X"] + r["m_Width"] + pad
    y1 = r["m_Y"] + r["m_Height"] + pad
    crop = img[max(0, y0) : y1, max(0, x0) : x1]
    return g, crop


def compare_glyph(char: str, point_size: int, pad: int, shipped: np.ndarray) -> dict:
    gen = render_glyph(str(FONT), char, point_size, pad, supersample=8)
    if gen is None or gen.bitmap.size == 0:
        return {"char": char, "ok": False, "why": "empty"}
    a, b = gen.bitmap.astype(np.float32), shipped.astype(np.float32)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    if h < 4 or w < 4:
        return {"char": char, "ok": False, "why": "tiny"}
    aa0 = a[:h, :w]
    bb = b[:h, :w]
    best_mae = 999.0
    best_band = 999.0
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            aa = np.roll(np.roll(aa0, dy, 0), dx, 1)
            mae = float(np.mean(np.abs(aa - bb)))
            band = (bb > 20) & (bb < 235)
            mae_band = float(np.mean(np.abs(aa - bb)[band])) if band.any() else mae
            if mae_band < best_band:
                best_band = mae_band
                best_mae = mae
    return {
        "char": char,
        "ok": best_band < 20,
        "mae": best_mae,
        "mae_band": best_band,
        "gen": gen.bitmap.shape,
        "ship": shipped.shape,
    }


def main() -> None:
    if not FONT.is_file():
        raise SystemExit(f"Police manquante: {FONT}")
    env, t, img = load_aldrich()
    try:
        pad = int(t["m_AtlasPadding"])
        pt = int(t["m_FaceInfo"]["m_PointSize"])
        print(f"Aldrich pt={pt} pad={pad} gradient={GRADIENT_SCALE}")
        print(f"shipped atlas {img.shape}, {len(t['m_CharacterTable'])} chars\n")

        results = []
        for c in t["m_CharacterTable"]:
            cp = c["m_Unicode"]
            if cp < 32 or cp > 126:
                continue
            char = chr(cp)
            g, crop = extract_shipped(t, img, cp, pad)
            if crop is None:
                continue
            results.append(compare_glyph(char, pt, pad, crop))

        results.sort(key=lambda r: -r.get("mae_band", 999))
        ok = sum(1 for r in results if r["ok"])
        print(f"{ok}/{len(results)} glyphes sous le seuil (mae_band < 20)\n")
        print("pires 12 :")
        for r in results[:12]:
            print(
                f"  {r['char']!r:5} mae={r.get('mae',0):5.1f}  "
                f"band={r.get('mae_band',0):5.1f}  "
                f"gen={r.get('gen')} ship={r.get('ship')}  "
                f"{'OK' if r['ok'] else 'KO'}"
            )
        median = float(np.median([r["mae_band"] for r in results]))
        print(f"\nmae_band median = {median:.1f}")
        if ok < len(results) * 0.85 or median > 15:
            raise SystemExit("Generateur trop eloigne de l'atlas livre — recalibrer.")
        print("\nValidation acceptable: on peut passer a l'injection.")
    finally:
        close_env(env)


if __name__ == "__main__":
    main()
