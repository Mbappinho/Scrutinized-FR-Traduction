# -*- coding: utf-8 -*-
"""Inspect Scrutinized's embedded SQLite (sharedassets4.asset.res5)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from game_paths import ROOT, game_root

REL = "Scrutinized_Data/sharedassets4.asset.res5"
OUT = ROOT / "source" / "phase4" / "sqlite_inventory.json"

# Tables / columns that carry player-visible English in the investigation loop.
TARGETS = [
    ("POI", "ID", "Report"),
    ("PoliceReport", "ID", "Description"),
    ("Convo", "ID", "Message"),
    ("SocialPost", "ID", "PostText"),
    ("SearchHistory", "ID", "Search"),
    ("ReceiptItem", "ID", "Item"),
]


def db_path() -> Path:
    return game_root() / REL


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    path = db_path()
    if not path.is_file():
        raise SystemExit(f"DB introuvable: {path}")
    magic = path.read_bytes()[:15]
    if magic != b"SQLite format 3":
        raise SystemExit(f"Pas une SQLite (magic={magic!r})")

    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    inv: dict = {
        "rel": REL,
        "size": path.stat().st_size,
        "sha256": sha256(path),
        "tables": {},
        "targets": {},
    }
    for t in tables:
        cols = [d[1] for d in cur.execute(f"PRAGMA table_info([{t}])").fetchall()]
        n = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        inv["tables"][t] = {"rows": n, "columns": cols}

    for table, pk, col in TARGETS:
        if table not in inv["tables"]:
            print(f"ABSENT {table}")
            continue
        rows = cur.execute(
            f"SELECT [{pk}] AS id, [{col}] AS text FROM [{table}] "
            f"WHERE [{col}] IS NOT NULL AND TRIM(CAST([{col}] AS TEXT)) != ''"
        ).fetchall()
        texts = []
        for r in rows:
            t = r["text"]
            if isinstance(t, bytes):
                t = t.decode("utf-8", errors="replace")
            texts.append({"id": r["id"], "text": t})
        chars = sum(len(r["text"] or "") for r in texts)
        sample = None
        for r in texts:
            if r["text"] and "restraining order" in r["text"]:
                sample = {"id": r["id"], "text": r["text"][:200]}
                break
        if sample is None and texts:
            sample = {"id": texts[0]["id"], "text": (texts[0]["text"] or "")[:200]}
        inv["targets"][f"{table}.{col}"] = {
            "pk": pk,
            "rows": len(texts),
            "chars": chars,
            "sample": sample,
        }
        print(
            f"{table}.{col}: {len(texts)} rows, {chars} chars, "
            f"sample_id={sample['id'] if sample else None}"
        )

    # Amelie Linter spot-check
    try:
        amelie = cur.execute(
            "SELECT ID, FirstName, LastName, Gender, HairColor, EyeColor, "
            "substr(Report,1,120) AS r FROM POI WHERE LastName LIKE 'Linter%'"
        ).fetchall()
        inv["amelie"] = [dict(r) for r in amelie]
        print("Amelie rows:", inv["amelie"])
    except Exception as e:
        print("Amelie query failed:", e)

    con.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(inv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Ecrit {OUT}")


if __name__ == "__main__":
    main()
