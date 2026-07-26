# -*- coding: utf-8 -*-
"""
Patch Scrutinized ZFBrowser browser_assets trailing plaintext web files.

Layout:
  [zfbRes + ZIP + EOCD][Foundation.css][Tutorial.html][TutorialControls.html][PNG…]

Each web file is replaced and padded to its original EN byte length so ZIP/PNG
offsets and any per-file size fields remain valid.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from game_paths import ROOT, browser_assets_path

EOCD_SIG = b"PK\x05\x06"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
DOCTYPE = b"<!DOCTYPE"

HTML_DIR = ROOT / "work" / "p0" / "html"
BACKUP_DIR = ROOT / "backup"


def find_eocd_end(data: bytes) -> int:
    pos = data.rfind(EOCD_SIG)
    if pos < 0:
        raise SystemExit("EOCD ZIP introuvable dans browser_assets")
    comment_len = int.from_bytes(data[pos + 20 : pos + 22], "little")
    end = pos + 22 + comment_len
    if end > len(data):
        raise SystemExit("EOCD comment depasse la fin du fichier")
    return end


def split_en_web(data: bytes) -> tuple[int, list[tuple[str, int, int]]]:
    """Return (span_start, [(name, start, end), ...]) for the three web files."""
    start = find_eocd_end(data)
    png = data.find(PNG_SIG, start)
    if png < 0:
        raise SystemExit("PNG signature introuvable apres zone web")
    chunk = data[start:png]
    d1 = chunk.find(DOCTYPE)
    d2 = chunk.find(DOCTYPE, d1 + 1)
    if d1 < 0 or d2 < 0:
        raise SystemExit("Deux documents HTML attendus apres CSS")
    # CSS / Tutorial / Controls
    parts = [
        ("Foundation.css", start, start + d1),
        ("Tutorial.html", start + d1, start + d2),
        ("TutorialControls.html", start + d2, png),
    ]
    return start, parts


def load_fr(name: str) -> bytes:
    """Load FR asset. HTML is re-encoded as Windows-1252 (ZFBrowser default)."""
    raw = (HTML_DIR / name).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    if name.endswith(".html"):
        text = raw.decode("utf-8")
        # normalize newlines then encode as cp1252 for in-game CEF/ZFBrowser
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        try:
            return text.encode("cp1252")
        except UnicodeEncodeError as exc:
            raise SystemExit(
                f"{name}: caractere non representable en windows-1252: {exc}"
            ) from exc
    # CSS: keep bytes, normalize CRLF only
    return raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def pad_to(blob: bytes, size: int, name: str) -> bytes:
    if len(blob) > size:
        raise SystemExit(f"{name}: FR trop long ({len(blob)} > {size} EN). Raccourcir le texte.")
    if len(blob) == size:
        return blob
    return blob + (b" " * (size - len(blob)))


def patch(apply_to_game: bool, dry_run: bool) -> None:
    src = browser_assets_path()
    data = bytearray(src.read_bytes())
    span_start, parts = split_en_web(data)
    png = parts[-1][2]
    print(f"Web span [{span_start}, {png}) total={png - span_start}")

    rebuilt = bytearray()
    for name, a, b in parts:
        en_len = b - a
        fr = pad_to(load_fr(name), en_len, name)
        print(f"  {name}: EN={en_len} FR_raw={len(load_fr(name))} padded={len(fr)}")
        rebuilt.extend(fr)

    if len(rebuilt) != (png - span_start):
        raise SystemExit("Taille reconstituee incoherente")

    if dry_run:
        print("Dry-run: OK, aucune ecriture.")
        return

    data[span_start:png] = rebuilt
    out_bytes = bytes(data)
    staged = ROOT / "build" / "browser_assets_fr"
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(out_bytes)
    print(f"Staged: {staged}")

    if apply_to_game:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = BACKUP_DIR / f"browser_assets.en.{stamp}.bak"
        shutil.copy2(src, backup)
        src.write_bytes(out_bytes)
        check = src.read_bytes()
        assert len(check) == len(data)
        assert b"Tutoriel Scrutinized" in check
        # Accents must be cp1252 single-byte, not UTF-8 mojibake sequence
        assert "Contrôles".encode("cp1252") in check
        assert b"Contr\xc3\xb4les" not in check  # UTF-8 "ô" must not remain
        assert check.find(PNG_SIG, span_start) == png
        print(f"Backup: {backup}")
        print(f"Patched: {src}")
        print("OK: taille inchangee, FR cp1252, PNG au meme offset.")
    else:
        print("Relancer avec --apply pour ecrire dans le jeu.")


def restore_latest() -> None:
    src = browser_assets_path()
    backups = sorted(BACKUP_DIR.glob("browser_assets.en.*.bak"))
    if not backups:
        raise SystemExit("Aucun backup dans backup/")
    latest = backups[-1]
    shutil.copy2(latest, src)
    print(f"Restore depuis {latest} -> {src}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch browser_assets tutos FR")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    if args.restore:
        restore_latest()
        return
    patch(apply_to_game=args.apply, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
