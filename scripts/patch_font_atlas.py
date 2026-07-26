# -*- coding: utf-8 -*-
"""
Expand a TMP SDF atlas to 1024x1024 and append French accent glyphs.

Existing glyphs are copied byte-for-byte from the shipped atlas — the generator
is only used for characters the atlas never had. Round letterforms (é, à, ô…)
are exactly where the generator matches the shipped encoding best.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from game_paths import ROOT, game_root
from sdf_atlas import charset_french, render_glyph
from text_render import ACCENTS_AVAILABLE  # noqa: F401 — docs cross-ref
from unity_env import close_env, load_env
from vanilla import restore, sha256, vanilla_path

FONTS_DIR = ROOT / "tools" / "fonts"
REPORT = ROOT / "build" / "font_atlas_report.json"

# Font asset location: (serialized file, path_id of TMP_FontAsset MonoBehaviour)
FONT_ASSETS = {
    "Aldrich-Regular SDF": ("Scrutinized_Data/sharedassets1.assets", None),
    "Lekton-Bold SDF": ("Scrutinized_Data/sharedassets1.assets", None),
    "Lekton-Regular SDF": ("Scrutinized_Data/sharedassets3.assets", None),
    "Lekton-Regular SDF2": ("Scrutinized_Data/sharedassets5.assets", None),
    "SpecialElite-Regular SDF": ("Scrutinized_Data/sharedassets1.assets", None),
    "Roboto-Regular SDF": ("Scrutinized_Data/sharedassets3.assets", None),
    "Roboto-Bold SDF": ("Scrutinized_Data/sharedassets3.assets", None),
    "Roboto-Black SDF": ("Scrutinized_Data/sharedassets3.assets", None),
    "typewcond_regular SDF": ("Scrutinized_Data/sharedassets3.assets", None),
    "typewcond_bold SDF": ("Scrutinized_Data/sharedassets0.assets", None),
    "COUR SDF": ("Scrutinized_Data/sharedassets3.assets", None),
}

FONT_FILES = {
    "Aldrich-Regular SDF": "Aldrich-Regular.ttf",
    "Lekton-Bold SDF": "Lekton-Bold.ttf",
    "Lekton-Regular SDF": "Lekton-Regular.ttf",
    "Lekton-Regular SDF2": "Lekton-Regular.ttf",
    "SpecialElite-Regular SDF": "SpecialElite-Regular.ttf",
    "Roboto-Regular SDF": "Roboto-Regular.ttf",
    "Roboto-Bold SDF": "Roboto-Bold.ttf",
    "Roboto-Black SDF": "Roboto-Black.ttf",
    "typewcond_regular SDF": "typewcond_regular.otf",
    "typewcond_bold SDF": "typewcond_bold.otf",
    "COUR SDF": "CourierNew-Regular.ttf",
}

# Characters we need beyond ASCII. Apostrophe/ellipsis already handled as ASCII
# in translations; keep the accented letters and French punctuation.
ACCENT_CHARS = list("àâäæçéèêëïîôœùûüÿÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ«»")


def find_font(env, name: str):
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if "m_FaceInfo" in t and t.get("m_Name") == name:
            return o, t
    return None, None


def read_atlas(env, font_tree) -> tuple[object, dict, np.ndarray]:
    by_id = {o.path_id: o for o in env.objects}
    tex_id = font_tree["m_AtlasTextures"][0]["m_PathID"]
    tex_obj = by_id[tex_id]
    tex = tex_obj.read_typetree()
    data = bytes(tex["image data"])
    img = np.frombuffer(data, dtype=np.uint8).reshape(tex["m_Height"], tex["m_Width"])
    return tex_obj, tex, img


def pack_into_free(
    atlas: np.ndarray,
    occupied_h: int,
    occupied_w: int,
    glyphs: list,
    padding: int,
) -> list:
    """Pack new glyph bitmaps into the free L-shaped region of an expanded atlas.

    Region A: right strip  [occupied_w .. W) x [0 .. occupied_h)
    Region B: bottom strip [0 .. W)          x [occupied_h .. H)
    """
    H, W = atlas.shape
    x, y, row_h = occupied_w, 0, 0
    in_right = True
    placed = []
    for g in sorted(glyphs, key=lambda g: -(g.bitmap.shape[0] * max(g.bitmap.shape[1], 1))):
        bh, bw = g.bitmap.shape
        if bw == 0 or bh == 0:
            placed.append(g)
            continue

        if in_right:
            if x + bw > W:
                x = occupied_w
                y += row_h
                row_h = 0
            if y + bh > occupied_h:
                in_right = False
                x, y, row_h = 0, occupied_h, 0

        if not in_right:
            if x + bw > W:
                x = 0
                y += row_h
                row_h = 0

        if y + bh > H or x + bw > W:
            raise SystemExit(
                f"Plus de place dans l'atlas {W}x{H} pour {g.char!r} "
                f"({bw}x{bh}) a ({x},{y})"
            )

        # Refuse to overwrite already-written free-region pixels.
        target = atlas[y : y + bh, x : x + bw]
        if target.max() > 0:
            raise SystemExit(
                f"Collision de packing pour {g.char!r} a ({x},{y}) "
                f"— le packer a reutilise une case deja remplie."
            )

        # Unity/TMP Alpha8 atlas rows are bottom-up in the serialized buffer
        # (vanilla 'A' is upside-down if you treat byte 0 as top). PIL bitmaps
        # are top-down — flip before blit or accents render under the letter.
        atlas[y : y + bh, x : x + bw] = g.bitmap[::-1]
        g.atlas_x = x + padding
        g.atlas_y = y + padding
        placed.append(g)
        x += bw
        row_h = max(row_h, bh)
    return placed


def next_glyph_index(font_tree: dict) -> int:
    return max((g["m_Index"] for g in font_tree["m_GlyphTable"]), default=-1) + 1


def expand_and_append_in_env(
    env,
    font_name: str,
    font_file: Path,
    dry_run: bool,
    atlas_override: np.ndarray | None = None,
    vanilla_tree: dict | None = None,
) -> dict:
    """Mutate one font asset inside an already-loaded environment. No file I/O.

    atlas_override / vanilla_tree: when patching the install, pass the pristine
    vanilla atlas and typetree so re-runs stay idempotent (reset to 512 + ASCII
    glyphs, then re-append accents) without wiping sibling text in the file.
    """
    font_obj, tree = find_font(env, font_name)
    if font_obj is None:
        raise SystemExit(f"{font_name} introuvable")

    if vanilla_tree is not None:
        # Reset glyph/char tables and atlas size to the shipped state.
        tree["m_GlyphTable"] = list(vanilla_tree["m_GlyphTable"])
        tree["m_CharacterTable"] = list(vanilla_tree["m_CharacterTable"])
        tree["m_AtlasWidth"] = vanilla_tree["m_AtlasWidth"]
        tree["m_AtlasHeight"] = vanilla_tree["m_AtlasHeight"]
        tree["m_FaceInfo"] = vanilla_tree["m_FaceInfo"]
        tree["m_AtlasPadding"] = vanilla_tree["m_AtlasPadding"]

    pad = int(tree["m_AtlasPadding"])
    pt = int(tree["m_FaceInfo"]["m_PointSize"])
    tex_obj, tex, old_live = read_atlas(env, tree)
    old = atlas_override if atlas_override is not None else old_live
    old_h, old_w = old.shape
    print(f"{font_name}: atlas source {old_w}x{old_h}, pt={pt}, pad={pad}")

    existing = {c["m_Unicode"] for c in tree["m_CharacterTable"]}
    missing = [ch for ch in ACCENT_CHARS if ord(ch) not in existing]
    probe = ImageFont.truetype(str(font_file), pt)
    drawable = []
    for ch in missing:
        try:
            if probe.getmask(ch).size[0] == 0:
                print(f"  skip {ch!r}: glyphe vide dans {font_file.name}")
                continue
        except Exception:
            print(f"  skip {ch!r}: non supporté par {font_file.name}")
            continue
        drawable.append(ch)
    print(f"  {len(drawable)} accents a ajouter: {''.join(drawable)}")

    new_glyphs = []
    for ch in drawable:
        g = render_glyph(str(font_file), ch, pt, pad, supersample=8)
        if g is None or (g.width == 0 and g.height == 0 and ch != " "):
            print(f"  skip {ch!r}: rendu SDF vide")
            continue
        new_glyphs.append(g)

    new_size = 1024
    atlas = np.zeros((new_size, new_size), dtype=np.uint8)
    atlas[:old_h, :old_w] = old
    placed = pack_into_free(atlas, old_h, old_w, new_glyphs, pad)

    next_idx = next_glyph_index(tree)
    glyph_entries = list(tree["m_GlyphTable"])
    char_entries = list(tree["m_CharacterTable"])
    added = []
    for g in placed:
        if g.width == 0 and g.height == 0:
            continue
        idx = next_idx
        next_idx += 1
        glyph_entries.append(
            {
                "m_Index": idx,
                "m_Metrics": {
                    "m_Width": float(g.width),
                    "m_Height": float(g.height),
                    "m_HorizontalBearingX": float(g.bearing_x),
                    "m_HorizontalBearingY": float(g.bearing_y),
                    "m_HorizontalAdvance": float(g.advance),
                },
                "m_GlyphRect": {
                    "m_X": int(g.atlas_x),
                    "m_Y": int(g.atlas_y),
                    "m_Width": int(g.width),
                    "m_Height": int(g.height),
                },
                "m_Scale": 1.0,
                "m_AtlasIndex": 0,
            }
        )
        char_entries.append(
            {
                "m_ElementType": 1,
                "m_Unicode": int(g.unicode),
                "m_GlyphIndex": idx,
                "m_Scale": 1.0,
            }
        )
        added.append(g.char)

    if dry_run:
        print(f"  dry-run: {len(added)} glyphes, atlas -> {new_size}x{new_size}")
        return {"font": font_name, "added": added, "dry_run": True}

    tex_data = tex_obj.read()
    tex_data.m_Width = new_size
    tex_data.m_Height = new_size
    tex_data.m_CompleteImageSize = int(new_size * new_size)
    tex_data.image_data = atlas.tobytes()
    if getattr(tex_data, "m_StreamData", None) is not None:
        try:
            tex_data.m_StreamData.offset = 0
            tex_data.m_StreamData.size = 0
            tex_data.m_StreamData.path = ""
        except Exception:
            pass
    tex_data.save()

    tree["m_GlyphTable"] = glyph_entries
    # TMP resolves characters by binary search on m_Unicode — unsorted = wrong glyphs.
    tree["m_CharacterTable"] = sorted(char_entries, key=lambda c: c["m_Unicode"])
    tree["m_AtlasWidth"] = new_size
    tree["m_AtlasHeight"] = new_size
    cs = tree.get("m_CreationSettings")
    if isinstance(cs, dict):
        cs["atlasWidth"] = new_size
        cs["atlasHeight"] = new_size
        tree["m_CreationSettings"] = cs
    font_obj.save_typetree(tree)

    by_id = {o.path_id: o for o in env.objects}
    mat_ref = tree.get("material") or {}
    mat_obj = by_id.get(mat_ref.get("m_PathID"))
    if mat_obj is not None:
        mat = mat_obj.read_typetree()
        floats = mat.get("m_SavedProperties", {}).get("m_Floats") or []
        new_floats = []
        for item in floats:
            if isinstance(item, dict):
                k, v = item.get("first"), item.get("second")
            else:
                k, v = item[0], item[1]
            if k in ("_TextureWidth", "_TextureHeight"):
                v = float(new_size)
            if isinstance(item, dict):
                new_floats.append({"first": k, "second": v})
            else:
                new_floats.append((k, v))
        mat["m_SavedProperties"]["m_Floats"] = new_floats
        mat_obj.save_typetree(mat)

    print(f"  +{len(added)} glyphes, atlas {new_size}")
    return {"font": font_name, "added": added, "atlas": new_size}


def apply_fonts(names: list[str], dry_run: bool) -> list[dict]:
    """Patch fonts on top of the current install.

    Shared files (sharedassets1/3/5) also carry translated text. Starting from
    vanilla here would wipe those translations, so we load the **install**, and
    pull the original 512x512 atlas bytes from the vanilla store only.
    """
    by_file: dict[str, list[str]] = {}
    for name in names:
        if name not in FONT_ASSETS:
            raise SystemExit(f"Police inconnue: {name}. Connues: {list(FONT_ASSETS)}")
        rel, _ = FONT_ASSETS[name]
        by_file.setdefault(rel, []).append(name)

    results = []
    for rel, font_names in sorted(by_file.items()):
        live = game_root() / rel
        src_vanilla = vanilla_path(rel)
        if not live.is_file():
            raise SystemExit(f"Install manquante: {rel}")
        # Vanilla env: source of pristine 512 atlases.
        van_env = load_env(src_vanilla)
        env = load_env(live)
        try:
            van_by_name = {}
            for name in font_names:
                obj, tree = find_font(van_env, name)
                if obj is None:
                    raise SystemExit(f"{name} absent du vanilla {rel}")
                van_by_name[name] = (obj, tree)

            for name in font_names:
                font_file = FONTS_DIR / FONT_FILES[name]
                if not font_file.is_file():
                    raise SystemExit(f"Fichier source manquant: {font_file}")
                van_obj, van_tree = van_by_name[name]
                _, _, van_atlas = read_atlas(van_env, van_tree)
                results.append(
                    {
                        **expand_and_append_in_env(
                            env,
                            name,
                            font_file,
                            dry_run,
                            atlas_override=van_atlas,
                            vanilla_tree=van_tree,
                        ),
                        "file": rel,
                    }
                )
            if not dry_run:
                live.write_bytes(env.file.save())
                print(f"  ecrit {rel}")
        finally:
            close_env(env)
            close_env(van_env)
    return results


def resolve_font_ids() -> None:
    """Fill path_ids by scanning once — prints a map for debugging."""
    for name, (rel, _) in FONT_ASSETS.items():
        env = load_env(vanilla_path(rel))
        try:
            obj, t = find_font(env, name)
            print(f"{name:30} {rel} #{obj.path_id if obj else 'ABSENT'}")
        finally:
            close_env(env)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Etendre les atlas TMP avec les accents FR")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--font", action="append", help="Nom TMP exact (repeatable)")
    ap.add_argument("--restore", action="store_true", help="Restaurer les assets touches")
    args = ap.parse_args()

    if args.list:
        resolve_font_ids()
        return

    if args.restore:
        files = sorted({rel for rel, _ in FONT_ASSETS.values()})
        restore(files)
        return

    if not (args.apply or args.dry_run):
        raise SystemExit("Specifier --dry-run, --apply, --list ou --restore")

    targets = args.font or list(FONT_ASSETS.keys())
    results = apply_fonts(targets, dry_run=args.dry_run)

    if args.apply:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Rapport: {REPORT}")


if __name__ == "__main__":
    main()
