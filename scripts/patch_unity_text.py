# -*- coding: utf-8 -*-
"""
Apply French text lots to the Unity serialized files.

Successor to patch_menus_fr.py. Two things changed and both matter:

- Entries are addressed by (file, path_id) instead of by searching raw bytes,
  so 'GAME' can no longer collide with an unrelated string.
- Each run rebuilds from the vanilla store rather than editing the live file,
  so patches never stack and length is unconstrained.

Because every run starts from vanilla, all lots are applied together by
default; patching a single lot would silently revert the others.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from game_paths import ROOT, game_root
from unity_env import (
    TEXT_FIELD,
    close_env,
    get_field,
    load_env,
    rect_transform,
    rect_width,
    set_field,
    size_delta_for,
)
from text_render import rendered, unrenderable
from vanilla import load_manifest, restore, sha256, vanilla_path

LOTS_DIR = ROOT / "work" / "lots"
BACKUP_DIR = ROOT / "backup" / "unity"
REPORT = ROOT / "build" / "unity_patch_report.json"
# Owned by other patchers — never reverted by this script.
FOREIGN = {
    "Scrutinized_Data/Resources/browser_assets",
    "Scrutinized_Data/Managed/Assembly-CSharp.dll",
    # SQLite enquête (patch_sqlite_fr) — hash != vanilla après P4
    "Scrutinized_Data/sharedassets4.asset.res5",
    # Atlas TMP only (patch_font_atlas) — pas de lot texte Unity
    "Scrutinized_Data/sharedassets0.assets",
}


def load_lots(only: str | None) -> list[dict]:
    if not LOTS_DIR.is_dir():
        raise SystemExit(f"Aucun lot dans {LOTS_DIR}")
    paths = sorted(LOTS_DIR.glob("*.json"))
    if only:
        paths = [p for p in paths if p.stem == only]
        if not paths:
            raise SystemExit(f"Lot introuvable: {only}")
    entries: list[dict] = []
    seen: dict[tuple[str, int, str], str] = {}
    for p in paths:
        lot = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(lot, dict):
            continue  # fragments / dumps temporaires
        for e in lot.get("entries", []):
            if "file" not in e or "path_id" not in e:
                continue  # lots DLL / schemas hors Unity
            field = e.get("field", TEXT_FIELD)
            key = (e["file"], int(e["path_id"]), field)
            if key in seen:
                raise SystemExit(f"Doublon {key} entre {seen[key]} et {p.name}")
            seen[key] = p.name
            entries.append({**e, "path_id": int(e["path_id"]), "field": field, "lot": p.stem})
    if not entries:
        raise SystemExit("Lots vides")
    return entries


def load_layout(only: str | None) -> list[dict]:
    """Box widenings, kept beside the text they exist to accommodate.

    French labels run roughly 20% longer than English, and word wrapping is on
    almost everywhere, so a label that no longer fits does not spill quietly:
    it wraps onto the row below. Where the surrounding layout has free space,
    growing the box is preferable to shortening the wording.
    """
    paths = sorted(LOTS_DIR.glob("*.json"))
    if only:
        paths = [p for p in paths if p.stem == only]
    items: list[dict] = []
    seen: dict[tuple[str, int], str] = {}
    for p in paths:
        lot = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(lot, dict):
            continue
        for it in lot.get("layout", []):
            if "file" not in it or "path_id" not in it:
                continue
            key = (it["file"], int(it["path_id"]))
            if key in seen:
                raise SystemExit(f"Layout en double {key} entre {seen[key]} et {p.name}")
            seen[key] = p.name
            items.append({**it, "path_id": int(it["path_id"]), "lot": p.stem})
    return items


def set_autosize(tree: dict, minimum: float, where: str) -> None:
    """Let TMP shrink the glyphs rather than wrap. Used where a label has no room
    to grow into. m_fontSizeMax is pinned to the current size so the text can
    only ever get smaller, never bigger."""
    if "m_enableAutoSizing" not in tree:
        raise SystemExit(f"{where}: pas un TextMeshPro, auto-taille impossible")
    tree["m_enableAutoSizing"] = True
    tree["m_fontSizeMin"] = float(minimum)
    tree["m_fontSizeMax"] = float(tree["m_fontSize"])


def resize_boxes(rel: str, by_id: dict, items: list[dict]) -> list[dict]:
    """Widths are rendered widths, not raw sizeDelta, so an entry means the same
    thing whether the rect stretches or not."""
    done = []
    for it in items:
        obj = by_id.get(it["path_id"])
        if obj is None:
            raise SystemExit(f"{rel}: path_id {it['path_id']} introuvable (layout)")
        rt = rect_transform(obj, by_id)
        if rt is None:
            raise SystemExit(f"{rel}#{it['path_id']}: pas de RectTransform")
        tree = rt.read_typetree()
        record = {**it, "before_w": rect_width(rt, by_id), "before_x": tree["m_AnchoredPosition"]["x"]}
        if "width" in it:
            tree["m_SizeDelta"]["x"] = size_delta_for(rt, by_id, it["width"])
        if "x" in it:
            tree["m_AnchoredPosition"]["x"] = float(it["x"])
        rt.save_typetree(tree)
        done.append(record)
    return done


def check_renderable(entries: list[dict]) -> None:
    """Accents are folded away on write, not forbidden in the lots. What must not
    happen is a character the folding table does not know, which would reach the
    atlas and draw as a blank."""
    bad = [(e, unrenderable(e["fr"])) for e in entries]
    bad = [(e, chars) for e, chars in bad if chars]
    if bad:
        lines = "\n".join(
            f'  {e["file"]}#{e["path_id"]}: {"".join(chars)} dans {e["fr"][:50]!r}'
            for e, chars in bad[:10]
        )
        raise SystemExit(
            "Caracteres sans equivalent ASCII connu :\n"
            f"{lines}\n"
            "Completer SUBSTITUTIONS dans scripts/text_render.py."
        )


def patch_file(
    rel: str, entries: list[dict], layout: list[dict]
) -> tuple[bytes, list[dict], list[dict]]:
    src = vanilla_path(rel)
    if not src.is_file():
        raise SystemExit(f"Vanilla manquant pour {rel}")
    env = load_env(src)
    try:
        by_id = {o.path_id: o for o in env.objects}
        applied = []
        # A single read/write cycle per object: dropdowns carry several fields,
        # and auto-sizing lives on the same component as the text. Writing them
        # in two passes would make the second one revert the first.
        by_object: dict[int, list[dict]] = {}
        for e in entries:
            by_object.setdefault(e["path_id"], []).append(e)
        autosize = {
            it["path_id"]: it["autosize_min"] for it in layout if "autosize_min" in it
        }
        for path_id in autosize:
            by_object.setdefault(path_id, [])

        for path_id, items in by_object.items():
            obj = by_id.get(path_id)
            if obj is None:
                raise SystemExit(f"{rel}: path_id {path_id} introuvable")
            tree = obj.read_typetree()
            changed = False
            for e in items:
                try:
                    current = get_field(tree, e["field"])
                except (KeyError, IndexError, TypeError):
                    raise SystemExit(
                        f"{rel}#{path_id}: champ {e['field']!r} absent"
                    ) from None
                if current != e["en"]:
                    raise SystemExit(
                        f"{rel}#{path_id} champ {e['field']}: texte EN inattendu.\n"
                        f"  lot     : {e['en']!r}\n"
                        f"  vanilla : {current!r}\n"
                        "  -> lot perime ou mise a jour Steam, relancer dump_unity_text.py"
                    )
                target = rendered(e["fr"])
                if target == e["en"]:
                    continue
                set_field(tree, e["field"], target)
                changed = True
                applied.append(e)
            if path_id in autosize:
                set_autosize(tree, autosize[path_id], f"{rel}#{path_id}")
                changed = True
            if changed:
                obj.save_typetree(tree)

        resized = resize_boxes(
            rel, by_id, [it for it in layout if "width" in it or "x" in it]
        )
        resized += [{**it} for it in layout if "autosize_min" in it and "width" not in it and "x" not in it]
        return env.file.save(), applied, resized
    finally:
        close_env(env)


def apply(dry_run: bool, only: str | None) -> None:
    entries = load_lots(only)
    check_renderable(entries)
    layout = load_layout(only)

    by_file: dict[str, list[dict]] = {}
    for e in entries:
        by_file.setdefault(e["file"], []).append(e)
    layout_by_file: dict[str, list[dict]] = {}
    for it in layout:
        layout_by_file.setdefault(it["file"], []).append(it)
        by_file.setdefault(it["file"], [])

    outputs: dict[str, bytes] = {}
    report = []
    resized_total = 0
    for rel, items in sorted(by_file.items()):
        data, applied, resized = patch_file(rel, items, layout_by_file.get(rel, []))
        outputs[rel] = data
        resized_total += len(resized)
        print(f"{len(applied):4d} / {len(items):<4d} {rel}")
        for e in applied:
            shown = rendered(e["fr"])
            folded = "  (accents replies)" if shown != e["fr"] else ""
            print(f"       {e['en'][:52]!r} -> {shown[:52]!r}{folded}")
        for it in resized:
            bits = []
            if "width" in it:
                bits.append(f"largeur {it['before_w']:.0f} -> {it['width']:.0f}")
            if "x" in it:
                bits.append(f"x {it['before_x']:.0f} -> {it['x']:.0f}")
            if "autosize_min" in it:
                bits.append(f"auto-taille min {it['autosize_min']:.0f}")
            print(f"       [boite] {it['path_id']} {', '.join(bits)}")
        report.extend(applied)

    # Files patched by an earlier run but no longer covered must go back to EN.
    stale = []
    for rel, meta in load_manifest()["files"].items():
        if rel in outputs or rel in FOREIGN:
            continue
        live = game_root() / rel
        if live.is_file() and sha256(live) != meta["sha256"]:
            stale.append(rel)

    if dry_run:
        if stale:
            print(f"\nA remettre en vanilla: {', '.join(stale)}")
        print("\nDry-run OK, aucune ecriture.")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for rel, data in outputs.items():
        dest = game_root() / rel
        if dest.is_file():
            shutil.copy2(dest, BACKUP_DIR / f"{rel.rsplit('/', 1)[-1]}.{stamp}.bak")
        dest.write_bytes(data)
        print(f"Ecrit {rel}")

    if stale:
        restore(stale)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {"stamp": stamp, "files": sorted(outputs), "entries": report},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"\n{len(report)} textes FR appliques, {resized_total} boites elargies. "
        f"Rapport: {REPORT}"
    )


def verify() -> None:
    """Re-read the live game files and confirm every FR string landed."""
    entries = load_lots(None)
    layout = load_layout(None)
    by_file: dict[str, list[dict]] = {}
    for e in entries:
        by_file.setdefault(e["file"], []).append(e)
    layout_by_file: dict[str, list[dict]] = {}
    for it in layout:
        layout_by_file.setdefault(it["file"], []).append(it)
        by_file.setdefault(it["file"], [])

    bad = 0
    for rel, items in sorted(by_file.items()):
        env = load_env(game_root() / rel)
        try:
            by_id = {o.path_id: o for o in env.objects}
            for e in items:
                obj = by_id.get(e["path_id"])
                try:
                    got = get_field(obj.read_typetree(), e["field"]) if obj else None
                except (KeyError, IndexError, TypeError):
                    got = None
                if got != rendered(e["fr"]):
                    bad += 1
                    print(
                        f"KO {rel}#{e['path_id']} {e['field']}: "
                        f"attendu {rendered(e['fr'])!r}, lu {got!r}"
                    )
            for it in layout_by_file.get(rel, []):
                obj = by_id.get(it["path_id"])
                rt = rect_transform(obj, by_id) if obj else None
                if rt is None:
                    bad += 1
                    print(f"KO {rel}#{it['path_id']}: RectTransform introuvable")
                    continue
                if "width" in it and round(rect_width(rt, by_id)) != round(it["width"]):
                    bad += 1
                    print(
                        f"KO {rel}#{it['path_id']} largeur: attendu {it['width']}, "
                        f"lu {rect_width(rt, by_id):.0f}"
                    )
                if "x" in it:
                    got = rt.read_typetree()["m_AnchoredPosition"]["x"]
                    if got != it["x"]:
                        bad += 1
                        print(f"KO {rel}#{it['path_id']} x: attendu {it['x']}, lu {got}")
                if "autosize_min" in it:
                    tt = obj.read_typetree()
                    if not tt.get("m_enableAutoSizing") or tt.get("m_fontSizeMin") != it["autosize_min"]:
                        bad += 1
                        print(
                            f"KO {rel}#{it['path_id']} auto-taille: "
                            f"active={tt.get('m_enableAutoSizing')} min={tt.get('m_fontSizeMin')}"
                        )
        finally:
            close_env(env)
    if bad:
        raise SystemExit(f"{bad} elements non conformes.")
    print(
        f"OK: {len(entries)} textes et {len(layout)} boites conformes dans l'install."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Appliquer les lots FR aux assets Unity")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true", help="Controler l'install apres patch")
    ap.add_argument("--restore", action="store_true", help="Tout remettre en EN vanilla")
    ap.add_argument("--lot", help="Nom d'un lot unique (deconseille: revert les autres)")
    args = ap.parse_args()

    if args.restore:
        rels = [r for r in load_manifest()["files"] if r not in FOREIGN]
        restore(rels)
        return
    if args.verify:
        verify()
        return
    if args.apply == args.dry_run:
        raise SystemExit("Choisir --apply ou --dry-run")
    apply(dry_run=args.dry_run, only=args.lot)


if __name__ == "__main__":
    main()
