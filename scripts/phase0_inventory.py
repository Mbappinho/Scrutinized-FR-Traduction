# -*- coding: utf-8 -*-
"""Phase 0 inventory: raw Unity asset strings + Mono DLL strings + SQLite probe.

UnityPy full load can hang on this title's assets; Phase 0 uses ASCII string
scans + optional light TextAsset probes instead.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from game_paths import ROOT, data_dir, game_root, managed_dir

PLAYER_STR_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9 \t\'\"\-\?\!\.\,\:\;\/\(\)\[\]\#\&\%\+\@]{2,180}$"
)
PATH_LIKE_RE = re.compile(
    r"^(?:[A-Za-z]:\\|/)?.+\.(html|css|js|png|jpg|jpeg|gif|dll|exe|unity3d|assets)$",
    re.I,
)
GUID_RE = re.compile(r"^[0-9a-fA-F-]{32,}$")
CAMEL_ONLY_RE = re.compile(r"^[A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)+$")

INTERESTING_KEYS = re.compile(
    r"(Threat|Report|Settings|Continue|Resume|Pause|Quit|Play|Hide|Open|Close|"
    r"ADOS|A\.D\.O\.S|Luna|Police|Evidence|Submit|Cancel|Back|Tutorial|"
    r"Window|Light|Door|Closet|Camera|Night|Save|Load|Options|Menu|SCRUT|"
    r"Kidnapper|Tanner|Router|Interact)",
    re.I,
)

ASSET_NAMES = [
    "resources.assets",
    "globalgamemanagers.assets",
    "sharedassets0.assets",
    "sharedassets1.assets",
    "sharedassets2.assets",
    "sharedassets4.assets",
    "sharedassets5.assets",
    "sharedassets6.assets",
    "sharedassets7.assets",
    "sharedassets8.assets",
    "sharedassets9.assets",
    "sharedassets3.assets",
    "level0",
    "level1",
    "level2",
    "level3",
    "level4",
    "level5",
    "level6",
    "level7",
    "level8",
    "level9",
]


def is_playerish(s: str) -> bool:
    s = s.strip()
    if len(s) < 3 or len(s) > 180:
        return False
    # Fast path: must look UI-related OR contain a space (sentence-like)
    if not INTERESTING_KEYS.search(s) and " " not in s:
        return False
    if PATH_LIKE_RE.match(s) or GUID_RE.match(s):
        return False
    if s.startswith(("m_", "k_", "Unity", "System.", "Mono.")):
        return False
    if CAMEL_ONLY_RE.match(s) and " " not in s:
        return False
    return bool(PLAYER_STR_RE.match(s))


def extract_ascii_strings(blob: bytes, min_len: int = 4):
    """Yield ASCII strings without materializing a giant list."""
    for m in re.finditer(rb"[\x20-\x7e]{%d,180}" % min_len, blob):
        yield m.group(0).decode("ascii")


def inventory_dll(dll_path: Path, out_csv: Path) -> dict:
    blob = dll_path.read_bytes()
    rows = []
    seen = set()
    total = 0
    for s in extract_ascii_strings(blob, 4):
        total += 1
        if not is_playerish(s) or s in seen:
            continue
        seen.add(s)
        rows.append(
            {
                "source": dll_path.name,
                "text": s,
                "interesting": bool(INTERESTING_KEYS.search(s)),
            }
        )
    rows.sort(key=lambda r: (not r["interesting"], r["text"].lower()))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "text", "interesting"])
        w.writeheader()
        w.writerows(rows)
    return {
        "dll": dll_path.name,
        "size": dll_path.stat().st_size,
        "ascii_strings_total": total,
        "playerish_unique": len(rows),
        "interesting_unique": sum(1 for r in rows if r["interesting"]),
        "interesting_samples": [r["text"] for r in rows if r["interesting"]][:80],
    }


def inventory_unity_raw(data: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    dedup: dict[str, dict] = {}
    scanned = []
    # Phase 0: only mid/small files; large sharedassets → AssetStudio in Phase 1
    allow = {
        "resources.assets",
        "sharedassets0.assets",
        "sharedassets2.assets",
        "sharedassets4.assets",
        "sharedassets5.assets",
        "sharedassets6.assets",
        "sharedassets7.assets",
        "sharedassets8.assets",
        "level0",
        "level1",
        "level2",
        "level4",
        "level5",
        "level6",
        "level7",
        "level8",
    }
    for name in ASSET_NAMES:
        p = data / name
        if not p.is_file():
            continue
        size = p.stat().st_size
        if name not in allow or size > 3_000_000:
            scanned.append(f"{name}:SKIPPED_{size}")
            continue
        scanned.append(f"{name}:{size}")
        print(f"  raw-scan {name} ({size // 1024} KB)…", flush=True)
        # Prefilter with interesting keywords in bytes for speed
        blob = p.read_bytes()
        for s in extract_ascii_strings(blob, 6):
            if is_playerish(s):
                dedup.setdefault(
                    s,
                    {
                        "container": name,
                        "text": s,
                        "interesting": bool(INTERESTING_KEYS.search(s)),
                    },
                )
    rows = sorted(dedup.values(), key=lambda r: (not r["interesting"], r["text"].lower()))
    with (out_dir / "raw_playerish_strings.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["container", "text", "interesting"])
        w.writeheader()
        w.writerows(rows)

    summary = {
        "method": "regex ASCII scan on small/mid assets only",
        "asset_files_scanned": scanned,
        "raw_playerish_unique": len(rows),
        "raw_interesting_unique": sum(1 for r in rows if r["interesting"]),
        "interesting_samples": [r["text"] for r in rows if r["interesting"]][:100],
        "textasset_count": 0,
        "unitypy_errors": [
            "UnityPy full load skipped (hang risk on this build). "
            "Use AssetStudio under tools/ for MonoBehaviour/TextAsset dump in Phase 1."
        ],
        "note": "globalgamemanagers/sharedassets1/3/9/level3/9 deferred — too large for Phase 0 ASCII pass.",
    }
    (out_dir / "unity_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def probe_sqlite() -> dict:
    install_dbs = []
    root = game_root()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            install_dbs.append(str(p))
        if p.suffix.lower() in {".bytes", ".dat"} and p.stat().st_size > 100:
            try:
                head = p.read_bytes()[:16]
            except OSError:
                continue
            if head.startswith(b"SQLite format 3"):
                install_dbs.append(str(p))

    local_low = Path.home() / "AppData" / "LocalLow" / "Reflect Studios"
    runtime = []
    if local_low.is_dir():
        for p in local_low.rglob("*"):
            if p.is_file():
                runtime.append({"path": str(p), "size": p.stat().st_size})

    return {
        "sqlite_in_install": install_dbs,
        "locallow_reflect_studios": runtime,
        "ormlite_present": (managed_dir() / "ServiceStack.OrmLite.Sqlite.dll").exists(),
        "sqlite_interop": (data_dir() / "Plugins" / "x86_64" / "SQLite.Interop.dll").exists(),
        "note": (
            "No .db in install or LocalLow (Player.log only). "
            "OrmLite/SQLite shipped — expect embedded or runtime DB."
        ),
    }


def read_unity_version() -> str:
    ggm = data_dir() / "globalgamemanagers"
    if not ggm.exists():
        return "unknown"
    m = re.search(rb"20\d{2}\.\d+\.\d+[a-z]\d+", ggm.read_bytes())
    return m.group(0).decode("ascii") if m else "unknown"


def read_buildid() -> str:
    acf = game_root().parents[1] / "appmanifest_1384770.acf"
    if not acf.exists():
        return ""
    m = re.search(r'"buildid"\s+"(\d+)"', acf.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else ""


def main() -> None:
    out = ROOT / "source" / "phase0"
    out.mkdir(parents=True, exist_ok=True)

    print("Scanning Unity assets (raw)…")
    unity_sum = inventory_unity_raw(data_dir(), out / "unity")

    dll_dir = out / "dll"
    dll_sum = []
    for name in ("Assembly-CSharp.dll", "Assembly-CSharp-firstpass.dll"):
        p = managed_dir() / name
        if p.exists():
            print(f"Scanning {name}…")
            dll_sum.append(inventory_dll(p, dll_dir / f"{name}.strings.csv"))

    sqlite = probe_sqlite()
    meta = {
        "game_root": str(game_root()),
        "unity_version": read_unity_version(),
        "buildid": read_buildid(),
        "mono": True,
        "il2cpp": (data_dir() / "il2cpp_data").exists(),
        "zfbrowser": True,
        "unity_inventory": unity_sum,
        "dll_inventory": dll_sum,
        "sqlite": sqlite,
    }
    (out / "inventory_summary.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
