# -*- coding: utf-8 -*-
"""
Vanilla EN reference store for Scrutinized.

Keeps an untouched copy of every serialized file we may patch, plus a SHA-256
manifest. The store is the single rollback source and doubles as a Steam-update
detector: if a file no longer matches the manifest and was not patched by us,
the game has been updated and every lot must be re-inventoried.

Streamed data (.resS / .resource / .res5) is never patched, so it stays out of
the store to keep it around 220 MB instead of 2.5 GB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from game_paths import ROOT, browser_assets_path, data_dir, game_root, managed_dir

VANILLA_DIR = ROOT / "backup" / "vanilla"
MANIFEST = ROOT / "work" / "vanilla_manifest.json"
APPID = "1384770"

SKIP_SUFFIXES = (".ress", ".resource", ".res5")

# Exception: this .res5 is actually a SQLite DB holding investigation text (P4).
SQLITE_TRACKED = ("Scrutinized_Data/sharedassets4.asset.res5",)

# Assemblies Mono dont le texte est patchable. Les autres DLL de Managed/ sont du
# moteur ou des greffons tiers et ne sont jamais touchees.
MANAGED_TRACKED = ("Assembly-CSharp.dll",)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked_relpaths() -> list[str]:
    """Serialized files we may patch, relative to the game root, posix-style."""
    root = game_root()
    out: list[str] = []
    for p in sorted(data_dir().iterdir()):
        if not p.is_file():
            continue
        low = p.name.lower()
        if low.endswith(SKIP_SUFFIXES):
            continue
        keep = (
            re.fullmatch(r"level\d+", low)
            or low.startswith("globalgamemanagers")
            or low == "resources.assets"
            or re.fullmatch(r"sharedassets\d+\.assets", low)
        )
        if keep:
            out.append(p.relative_to(root).as_posix())
    ba = browser_assets_path()
    if ba.is_file():
        out.append(ba.relative_to(root).as_posix())
    for name in MANAGED_TRACKED:
        dll = managed_dir() / name
        if dll.is_file():
            out.append(dll.relative_to(root).as_posix())
    for rel in SQLITE_TRACKED:
        if (root / rel).is_file():
            out.append(rel)
    return out


def read_buildid() -> str | None:
    acf = game_root().parents[1] / f"appmanifest_{APPID}.acf"
    if not acf.is_file():
        return None
    m = re.search(r'"buildid"\s+"(\d+)"', acf.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def vanilla_path(rel: str) -> Path:
    return VANILLA_DIR / rel


def _vanilla_source(rel: str) -> tuple[Path, str]:
    """Where the untouched EN bytes live: an early backup, else the install."""
    name = rel.rsplit("/", 1)[-1]
    if name == "browser_assets":
        baks = sorted((ROOT / "backup").glob("browser_assets.en.*.bak"))
        if baks:
            return baks[0], f"backup/{baks[0].name}"
    baks = sorted((ROOT / "backup" / "menus").glob(f"{name}.*.bak"))
    if baks:
        return baks[0], f"backup/menus/{baks[0].name}"
    return game_root() / rel, "install"


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        raise SystemExit(f"Manifeste absent: {MANIFEST}. Lancer: python scripts/vanilla.py --init")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def restore(rels: list[str]) -> None:
    """Copy vanilla EN bytes back over the install."""
    for rel in rels:
        src = vanilla_path(rel)
        if not src.is_file():
            raise SystemExit(f"Pas de vanilla pour {rel}. Lancer --init d'abord.")
        dest = game_root() / rel
        shutil.copy2(src, dest)
        print(f"Restore vanilla {rel}")


def init(force: bool) -> None:
    rels = tracked_relpaths()
    if not rels:
        raise SystemExit("Aucun fichier serialise trouve.")
    entries: dict[str, dict] = {}
    copied = kept = 0

    for rel in rels:
        src, origin = _vanilla_source(rel)
        dest = vanilla_path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and not force:
            kept += 1
        else:
            shutil.copy2(src, dest)
            copied += 1
        entries[rel] = {
            "size": dest.stat().st_size,
            "sha256": sha256(dest),
            "source": origin,
        }
        print(f"  {rel}  <- {origin}")

    manifest = {
        "meta": {
            "game": "Scrutinized",
            "appid": APPID,
            "buildid": read_buildid(),
            "unity": "2019.4.7f1",
            "created": datetime.now().isoformat(timespec="seconds"),
            "note": (
                "SHA-256 des fichiers serialises EN d'origine. Les .resS/.resource/.res5 "
                "sont hors manifeste SAUF sharedassets4.asset.res5 (SQLite boucle enquete)."
            ),
        },
        "files": entries,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(e["size"] for e in entries.values())
    print(
        f"\nVanilla store: {len(entries)} fichiers ({total / 1e6:.1f} Mo), "
        f"{copied} copies, {kept} deja presents"
    )
    print(f"Manifeste: {MANIFEST}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Store vanilla EN + manifeste SHA-256")
    ap.add_argument("--init", action="store_true", help="Construire le store et le manifeste")
    ap.add_argument("--force", action="store_true", help="Re-copier meme si deja present")
    ap.add_argument("--restore-all", action="store_true", help="Tout remettre en EN vanilla")
    args = ap.parse_args()
    if args.restore_all:
        restore(list(load_manifest()["files"]))
        return
    if args.init:
        init(force=args.force)
        return
    raise SystemExit("Specifier --init, --force ou --restore-all")


if __name__ == "__main__":
    main()
