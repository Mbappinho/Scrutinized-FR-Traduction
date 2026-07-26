# -*- coding: utf-8 -*-
"""
Compare the Steam install against the vanilla manifest.

Reports each tracked file as vanilla / patched / missing, checks the vanilla
store itself has not rotted, and flags a Steam update via the BuildID.

Exit code is non-zero when the rollback path is compromised (store corrupt or
BuildID changed), so it can gate a patch run.
"""
from __future__ import annotations

import argparse

from game_paths import game_root
from vanilla import (
    load_manifest,
    read_buildid,
    sha256,
    tracked_relpaths,
    vanilla_path,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Verifier l'integrite install vs vanilla")
    ap.add_argument("--quiet", action="store_true", help="N'afficher que les anomalies")
    args = ap.parse_args()

    manifest = load_manifest()
    files = manifest["files"]
    expected_build = manifest["meta"].get("buildid")
    current_build = read_buildid()

    vanilla_ok = patched = missing = store_bad = 0
    problems: list[str] = []

    for rel, entry in files.items():
        live = game_root() / rel
        if not live.is_file():
            missing += 1
            problems.append(f"MANQUANT   {rel}")
            continue
        live_hash = sha256(live)
        if live_hash == entry["sha256"]:
            vanilla_ok += 1
            if not args.quiet:
                print(f"vanilla    {rel}")
        else:
            patched += 1
            if not args.quiet:
                print(f"PATCHE     {rel}")

        store = vanilla_path(rel)
        if not store.is_file():
            store_bad += 1
            problems.append(f"STORE ABSENT  {rel}")
        elif sha256(store) != entry["sha256"]:
            store_bad += 1
            problems.append(f"STORE CORROMPU {rel}")

    untracked = [r for r in tracked_relpaths() if r not in files]
    for rel in untracked:
        problems.append(f"HORS MANIFESTE {rel}")

    print(
        f"\n{vanilla_ok} vanilla, {patched} patches, {missing} manquants, "
        f"{len(untracked)} hors manifeste"
    )

    build_changed = expected_build and current_build and expected_build != current_build
    if build_changed:
        problems.append(f"BUILDID {expected_build} -> {current_build} (maj Steam)")

    if problems:
        print("\nAnomalies:")
        for p in problems:
            print(f"  {p}")

    if store_bad or build_changed or missing:
        raise SystemExit(1)
    print("\nRollback disponible, BuildID inchange.")


if __name__ == "__main__":
    main()
