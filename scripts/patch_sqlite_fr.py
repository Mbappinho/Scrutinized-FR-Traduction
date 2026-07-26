# -*- coding: utf-8 -*-
"""
Patch French text into Scrutinized's embedded SQLite (sharedassets4.asset.res5).

Lots live in work/lots/p4_*.json with entries:
  { "id": <pk>, "en": "...", "fr": "..." }

Matching is by primary key + exact EN guard (refuse if live EN != lot EN).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from game_paths import ROOT, game_root
from text_render import rendered
from vanilla import restore, sha256, vanilla_path

REL = "Scrutinized_Data/sharedassets4.asset.res5"
REPORT = ROOT / "build" / "sqlite_patch_report.json"

# lot file stem -> (table, pk_col, text_col)
LOT_MAP = {
    "p4_poi": ("POI", "ID", "Report"),
    "p4_police": ("PoliceReport", "ID", "Description"),
    "p4_sms": ("Convo", "ID", "Message"),
    "p4_social": ("SocialPost", "ID", "PostText"),
    "p4_search": ("SearchHistory", "ID", "Search"),
    "p4_receipt": ("ReceiptItem", "ID", "Item"),
}


def live_path() -> Path:
    return game_root() / REL


def load_lot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def export_lot(name: str, out: Path | None = None) -> Path:
    """Dump EN rows from the vanilla (or live) DB into a lot skeleton."""
    table, pk, col = LOT_MAP[name]
    src = vanilla_path(REL)
    if not src.is_file():
        src = live_path()
    con = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        f"SELECT [{pk}] AS id, [{col}] AS en FROM [{table}] "
        f"WHERE [{col}] IS NOT NULL AND TRIM(CAST([{col}] AS TEXT)) != '' ORDER BY [{pk}]"
    ).fetchall()
    con.close()
    entries = []
    for r in rows:
        en = r["en"]
        if isinstance(en, bytes):
            en = en.decode("utf-8", errors="replace")
        entries.append({"id": r["id"], "en": en, "fr": en})
    lot = {
        "lot": name,
        "scope": f"{table}.{col} dans {REL}",
        "table": table,
        "pk": pk,
        "column": col,
        "note": "Traduire fr. Ne pas toucher Gender/HairColor/EyeColor (enums / compares).",
        "entries": entries,
    }
    dest = out or (ROOT / "work" / "lots" / f"{name}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(lot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Export {name}: {len(lot['entries'])} entrees -> {dest}")
    return dest


def apply_lots(lot_names: list[str], dry_run: bool) -> dict:
    live = live_path()
    if not live.is_file():
        raise SystemExit(f"Install manquante: {REL}")
    van = vanilla_path(REL)
    if not van.is_file():
        raise SystemExit(f"Vanilla manquant: {van}. Lancer scripts/vanilla.py --init")

    # Work on a temp copy of vanilla, then replace live (idempotent).
    tmp = Path(tempfile.mkstemp(suffix=".sqlite")[1])
    shutil.copy2(van, tmp)

    report = {"file": REL, "dry_run": dry_run, "lots": [], "updated": 0, "skipped": 0, "errors": []}
    con = sqlite3.connect(str(tmp))
    try:
        for name in lot_names:
            if name not in LOT_MAP:
                raise SystemExit(f"Lot inconnu: {name}. Connus: {list(LOT_MAP)}")
            table, pk, col = LOT_MAP[name]
            path = ROOT / "work" / "lots" / f"{name}.json"
            lot = load_lot(path)
            lot_rep = {"lot": name, "table": table, "ok": 0, "skip_same": 0, "errors": []}
            for e in lot["entries"]:
                eid = e["id"]
                en = e["en"]
                fr = rendered(e["fr"])
                if not fr or fr == en:
                    # Still write FR if accents-only change vs raw en; if identical, skip.
                    if fr == en:
                        lot_rep["skip_same"] += 1
                        report["skipped"] += 1
                        continue
                row = con.execute(
                    f"SELECT [{col}] AS t FROM [{table}] WHERE [{pk}] = ?", (eid,)
                ).fetchone()
                if row is None:
                    msg = f"{table} id={eid} absent"
                    lot_rep["errors"].append(msg)
                    report["errors"].append(msg)
                    continue
                live_en = row[0]
                if isinstance(live_en, bytes):
                    live_en = live_en.decode("utf-8", errors="replace")
                if live_en != en:
                    # Vanilla should match lot EN; if not, Steam update or bad lot.
                    msg = f"{table} id={eid}: EN lot != vanilla (maj Steam?)"
                    lot_rep["errors"].append(msg)
                    report["errors"].append(msg)
                    continue
                if dry_run:
                    lot_rep["ok"] += 1
                    report["updated"] += 1
                    continue
                con.execute(
                    f"UPDATE [{table}] SET [{col}] = ? WHERE [{pk}] = ?", (fr, eid)
                )
                lot_rep["ok"] += 1
                report["updated"] += 1
            report["lots"].append(lot_rep)
            print(
                f"{name}: {lot_rep['ok']} maj, {lot_rep['skip_same']} identiques, "
                f"{len(lot_rep['errors'])} erreurs"
            )
        if not dry_run:
            con.commit()
    finally:
        con.close()

    if dry_run:
        try:
            tmp.unlink(missing_ok=True)
        except PermissionError:
            pass
    else:
        if report["errors"]:
            try:
                tmp.unlink(missing_ok=True)
            except PermissionError:
                pass
            raise SystemExit(f"{len(report['errors'])} erreurs — install non modifiee")
        shutil.copy2(tmp, live)
        try:
            tmp.unlink(missing_ok=True)
        except PermissionError:
            pass
        print(f"Ecrit {live} ({live.stat().st_size} octets)")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Rapport: {REPORT}")
    return report


def verify() -> None:
    live = live_path()
    van = vanilla_path(REL)
    print(f"live  {sha256(live)}")
    print(f"vanil {sha256(van)}")
    print("patched" if sha256(live) != sha256(van) else "identical to vanilla")


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch FR de la SQLite enquete")
    ap.add_argument("--export", metavar="LOT", help="Exporter un lot (p4_poi, …)")
    ap.add_argument("--export-all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lot", action="append", help="Lot a appliquer (repeatable)")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    if args.export:
        export_lot(args.export)
        return
    if args.export_all:
        for name in LOT_MAP:
            export_lot(name)
        return
    if args.restore:
        restore([REL])
        return
    if args.verify:
        verify()
        return
    if args.apply or args.dry_run:
        names = args.lot or list(LOT_MAP)
        apply_lots(names, dry_run=args.dry_run)
        return
    raise SystemExit("Choisir --export / --export-all / --apply / --dry-run / --restore / --verify")


if __name__ == "__main__":
    main()
