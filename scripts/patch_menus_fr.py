# -*- coding: utf-8 -*-
"""
DEPRECATED. Superseded by patch_unity_text.py — do not run.

Kept as a documented fallback in case the UnityPy pipeline ever breaks. It
edits bytes in place, so it can only shorten strings (CONTINUE -> CONTINU.),
and it would start from an already-patched install rather than the vanilla
store. See docs/PATCH_MENUS_FR.md.

Unity format: int32 length (UTF-8 bytes, no null) + data + pad to 4-byte align.
CRITICAL: never change the length field — FR must be UTF-8 ≤ EN, then pad with
spaces to the exact EN byte length. Changing length breaks ScriptableObject
layouts (TitleTipData: "Read N bytes but expected M" → Crash).

Lekton TMP atlas lacks French glyphs — keep UI FR ASCII-only (no accents).
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
from datetime import datetime
from pathlib import Path

from game_paths import ROOT, data_dir

LOT = ROOT / "work" / "p0" / "menus_en_fr.json"
BACKUP_DIR = ROOT / "backup" / "menus"


def align4(n: int) -> int:
    return (n + 3) & ~3


def build_record(text_bytes: bytes) -> bytes:
    """Unity string: length + UTF-8 bytes + align4 padding (no embedded NUL)."""
    n = len(text_bytes)
    body = text_bytes + (b"\x00" * (align4(n) - n))
    return struct.pack("<I", n) + body


def patch_blob(blob: bytearray, en: str, fr: str) -> int:
    en_b = en.encode("utf-8")
    fr_b = fr.encode("utf-8")
    if len(fr_b) > len(en_b):
        raise SystemExit(
            f"FR trop long ({len(fr_b)}>{len(en_b)}): {en!r} -> {fr!r}"
        )
    # Keep length field identical — pad with spaces (visible as trailing space in UI).
    padded = fr_b + (b" " * (len(en_b) - len(fr_b)))
    old = build_record(en_b)
    new = build_record(padded)
    if len(old) != len(new):
        raise SystemExit(f"Slot size mismatch for {en!r}")
    if old[:4] != new[:4]:
        raise SystemExit(f"Length field must not change for {en!r}")
    count = 0
    start = 0
    while True:
        i = blob.find(old, start)
        if i < 0:
            break
        blob[i : i + len(old)] = new
        count += 1
        start = i + len(new)
    return count


def load_lot() -> dict:
    return json.loads(LOT.read_text(encoding="utf-8"))


def apply(dry_run: bool) -> None:
    lot = load_lot()
    data = data_dir()
    touched: dict[str, bytearray] = {}
    report = []

    for pair in lot["pairs"]:
        en, fr = pair["en"], pair["fr"]
        containers = pair.get("containers") or []
        total = 0
        for name in containers:
            path = data / name
            if not path.is_file():
                raise SystemExit(f"Manquant: {path}")
            if name not in touched:
                touched[name] = bytearray(path.read_bytes())
            n = patch_blob(touched[name], en, fr)
            total += n
        report.append({"en": en, "fr": fr, "replacements": total})
        print(f"{total:2d}x  {en!r} -> {fr!r}")

    missing = [r for r in report if r["replacements"] == 0]
    if missing:
        raise SystemExit(f"Aucune occurrence pour: {[m['en'] for m in missing]}")

    if dry_run:
        print("Dry-run OK, aucune ecriture.")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for name, blob in touched.items():
        src = data / name
        bak = BACKUP_DIR / f"{name}.{stamp}.bak"
        shutil.copy2(src, bak)
        src.write_bytes(blob)
        print(f"Patched {name} (backup {bak.name})")
    (ROOT / "build" / "menus_patch_report.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "build" / "menus_patch_report.json").write_text(
        json.dumps({"stamp": stamp, "report": report}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("OK menus P0 appliques.")


def _stamps() -> list[str]:
    return sorted(
        {
            p.name.rsplit(".", 2)[1]
            for p in BACKUP_DIR.glob("*.bak")
            if len(p.name.rsplit(".", 2)) == 3 and p.name.rsplit(".", 2)[1][:8].isdigit()
        }
    )


def restore_latest() -> None:
    if not BACKUP_DIR.is_dir():
        raise SystemExit("Pas de backup menus/")
    stamps = _stamps()
    if not stamps:
        raise SystemExit("Aucun .bak")
    latest = stamps[-1]
    for p in BACKUP_DIR.glob(f"*.{latest}.bak"):
        base = p.name.replace(f".{latest}.bak", "")
        dest = data_dir() / base
        shutil.copy2(p, dest)
        print(f"Restore {base} <- {p.name}")


def restore_vanilla() -> None:
    """Restore the oldest stamp (first backup = closest to EN vanilla)."""
    if not BACKUP_DIR.is_dir():
        raise SystemExit("Pas de backup menus/")
    stamps = _stamps()
    if not stamps:
        raise SystemExit("Aucun stamp")
    stamp = stamps[0]
    for p in BACKUP_DIR.glob(f"*.{stamp}.bak"):
        base = p.name.replace(f".{stamp}.bak", "")
        dest = data_dir() / base
        shutil.copy2(p, dest)
        print(f"Restore vanilla {base} <- {p.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument(
        "--restore-vanilla",
        action="store_true",
        help="Restore oldest menus backup (EN before first patch)",
    )
    args = ap.parse_args()
    if args.restore_vanilla:
        restore_vanilla()
        return
    if args.restore:
        restore_latest()
        return
    if args.apply and args.dry_run:
        raise SystemExit("Choisir --apply ou --dry-run, pas les deux")
    if not args.apply and not args.dry_run:
        raise SystemExit("Specifier --apply, --dry-run, --restore ou --restore-vanilla")
    apply(dry_run=not args.apply)


if __name__ == "__main__":
    main()
