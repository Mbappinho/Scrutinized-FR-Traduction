# -*- coding: utf-8 -*-
"""
Repaint WASD tutorial key PNGs to ZQSD inside browser_assets (zfbRes pool).

Targets (index offsets into Scrutinized_Data/Resources/browser_assets):
  /Tutorial/WASDF.png
  /Tutorial/wasdKeys.png

New PNG must be <= vanilla size; trailing bytes are zero-padded so the index
size field stays valid. Always starts from vanilla browser_assets when used
via --apply-from-vanilla; otherwise patches the live file in place after
HTML FR has been applied (same blob offsets — HTML pad keeps sizes).
"""
from __future__ import annotations

import argparse
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from game_paths import ROOT, browser_assets_path
from vanilla import vanilla_path

BROWSER_REL = "Scrutinized_Data/Resources/browser_assets"
OUT_DIR = ROOT / "build" / "azerty_pngs"

# Letter swaps on the painted keycaps (physical WASD positions -> AZERTY labels).
LETTER_MAP = {"W": "Z", "A": "Q"}


def _index_png_slots(data: bytes) -> dict[str, tuple[int, int]]:
    """Return {path: (offset, size)} for leaf PNG entries in the zfbRes index."""
    pos = data.find(b"/Foundation.css") - 1
    if pos < 0 or data[pos] != len("/Foundation.css"):
        raise SystemExit("Index zfbRes: /Foundation.css introuvable")
    slots: dict[str, tuple[int, int]] = {}
    n = 0
    while n < 120:
        ln = data[pos]
        if not (1 <= ln <= 220):
            break
        path = data[pos + 1 : pos + 1 + ln]
        if not path.startswith(b"/") or not all(32 <= c < 127 for c in path):
            break
        path_s = path.decode("ascii")
        pos += 1 + ln
        off = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        _unk = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        size = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if path_s.endswith(".png"):
            slots[path_s] = (off, size)
        n += 1
    return slots


def _key_gray(img: Image.Image, cx: int, cy: int) -> tuple[int, int, int]:
    """Sample a mid-gray from the key face near the letter."""
    px = img.load()
    w, h = img.size
    for r in range(8, 28):
        for dx, dy in ((0, -r), (-r, 0), (r, 0), (0, r)):
            x, y = cx + dx, cy + dy
            if 0 <= x < w and 0 <= y < h:
                p = px[x, y]
                if p[0] == p[1] == p[2] and 40 < p[0] < 120:
                    return p[0], p[1], p[2]
    return 70, 70, 70


def _bright_centroids(img: Image.Image) -> list[tuple[float, float, int, int, int, int]]:
    """Return list of (cx, cy, x0, y0, x1, y1) for bright letter blobs."""
    gray = img.convert("RGBA")
    px = gray.load()
    w, h = gray.size
    visited = [[False] * w for _ in range(h)]
    blobs: list[tuple[float, float, int, int, int, int]] = []

    def bright(x, y) -> bool:
        r, g, b, a = px[x, y]
        return a > 200 and r > 200 and g > 200 and b > 200

    for y in range(h):
        for x in range(w):
            if visited[y][x] or not bright(x, y):
                continue
            stack = [(x, y)]
            visited[y][x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx] and bright(nx, ny):
                        visited[ny][nx] = True
                        stack.append((nx, ny))
            if len(cells) < 40 or len(cells) > 2500:
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            if x1 - x0 < 8 or y1 - y0 < 10:
                continue
            blobs.append(((x0 + x1) / 2, (y0 + y1) / 2, x0, y0, x1, y1))
    return blobs


def _classify_wasd(blobs: list[tuple[float, float, int, int, int, int]]) -> dict[str, tuple]:
    """Map W/A/S/D(/F) from blob positions."""
    if len(blobs) < 4:
        raise SystemExit(f"Trop peu de glyphes detectes ({len(blobs)})")
    # Top-most is W (or alone on first row)
    by_y = sorted(blobs, key=lambda b: b[1])
    top = by_y[0]
    rest = by_y[1:]
    # Bottom row: leftmost A, then S, D, optional F
    row = sorted(rest, key=lambda b: b[0])
    out = {"W": top, "A": row[0], "S": row[1], "D": row[2]}
    if len(row) >= 4:
        out["F"] = row[3]
    return out


def repaint_zqsd(src_png: bytes) -> bytes:
    img = Image.open(io.BytesIO(src_png)).convert("RGBA")
    blobs = _bright_centroids(img)
    keys = _classify_wasd(blobs)
    draw = ImageDraw.Draw(img)

    # Prefer a bold sans if available; fall back to default.
    font = None
    for candidate in (
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        ROOT / "tools" / "fonts" / "SpecialElite-Regular.ttf",
    ):
        if candidate.is_file():
            font_path = candidate
            break
    else:
        font_path = None

    for old, new in LETTER_MAP.items():
        if old not in keys:
            continue
        cx, cy, x0, y0, x1, y1 = keys[old]
        pad = 4
        box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        fill = _key_gray(img, int(cx), int(cy))
        draw.rectangle(box, fill=fill + (255,))
        bh = y1 - y0
        size = max(18, int(bh * 1.35))
        if font_path:
            font = ImageFont.truetype(str(font_path), size)
        else:
            font = ImageFont.load_default()
        # Center text in box
        bbox = draw.textbbox((0, 0), new, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = cx - tw / 2 - bbox[0]
        ty = cy - th / 2 - bbox[1]
        draw.text((tx, ty), new, fill=(255, 255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def patch_browser_pngs(data: bytearray, dry_run: bool = False) -> list[dict]:
    slots = _index_png_slots(bytes(data))
    report = []
    for path in ("/Tutorial/WASDF.png", "/Tutorial/wasdKeys.png"):
        if path not in slots:
            raise SystemExit(f"{path} absent de l'index zfbRes")
        off, size = slots[path]
        raw = bytes(data[off : off + size])
        if not raw.startswith(b"\x89PNG"):
            raise SystemExit(f"{path}: pas un PNG a offset {off}")
        # Strip trailing padding from a previous patch if any
        iend = raw.find(b"IEND")
        if iend > 0:
            raw = raw[: iend + 8]
        new = repaint_zqsd(raw)
        if len(new) > size:
            # Retry with stronger compress / smaller font by re-encoding RGB
            img = Image.open(io.BytesIO(new)).convert("RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True, compress_level=9)
            new = buf.getvalue()
        if len(new) > size:
            raise SystemExit(
                f"{path}: PNG ZQSD trop long ({len(new)} > {size}). "
                "Resserrer le dessin."
            )
        padded = new + (b"\x00" * (size - len(new)))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        preview = OUT_DIR / (path.lstrip("/").replace("/", "_") + ".zqsd.png")
        preview.write_bytes(new)
        print(f"  {path}: {len(raw)} -> {len(new)} (pad {size - len(new)}) preview={preview}")
        report.append({"path": path, "offset": off, "slot": size, "png": len(new)})
        if not dry_run:
            data[off : off + size] = padded
    return report


def apply(from_vanilla: bool, dry_run: bool) -> None:
    if from_vanilla:
        src = vanilla_path(BROWSER_REL)
        if not src.is_file():
            raise SystemExit(f"Vanilla manquant: {BROWSER_REL}")
        data = bytearray(src.read_bytes())
    else:
        data = bytearray(browser_assets_path().read_bytes())
    patch_browser_pngs(data, dry_run=dry_run)
    if dry_run:
        print("Dry-run OK, aucune ecriture.")
        return
    dest = browser_assets_path()
    dest.write_bytes(data)
    print(f"Ecrit {dest} ({len(data)} octets)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Repaint WASD tutorial PNGs -> ZQSD")
    ap.add_argument("--apply", action="store_true", help="Ecrire dans browser_assets live")
    ap.add_argument(
        "--from-vanilla",
        action="store_true",
        help="Partir du vanilla (sinon patche le fichier live)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.apply and not args.dry_run:
        ap.error("Specifier --apply ou --dry-run")
    apply(from_vanilla=args.from_vanilla, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
