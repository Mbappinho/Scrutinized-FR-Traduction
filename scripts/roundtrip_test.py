# -*- coding: utf-8 -*-
"""
Blocking gate before any UnityPy-based patching.

Re-serializing a Unity file is the real risk of this pipeline: if UnityPy
cannot reproduce a file the engine still accepts, the approach is dead and we
fall back to the byte patcher.

Two levels of proof:

1. Offline. Save a vanilla file unchanged and diff it. UnityPy pads the total
   file size up to an 8-byte boundary, so a legitimate result is either byte
   identical, or identical except the header file_size field plus trailing
   zeros. Anything else is a red flag.
2. In-game. --install writes the re-serialized files into the game so the
   engine itself can pass judgement; --restore rolls back.

Texts are re-read from a temporary copy inside the vanilla store, because
resolving m_Script pointers needs the sibling serialized files next to it.

The list of files to test is derived from the lots, so the gate always covers
exactly what the patcher writes. A hardcoded list would have kept passing while
P2 started writing to sharedassets5 and sharedassets9 untested.
"""
from __future__ import annotations

import argparse
import json
import shutil

from game_paths import ROOT, game_root
from unity_env import close_env, iter_texts, load_env
from vanilla import restore, vanilla_path

OUT_DIR = ROOT / "build" / "roundtrip"
LOTS_DIR = ROOT / "work" / "lots"


def patched_files() -> list[str]:
    """Every serialized file the lots touch, in a stable order."""
    files = set()
    for path in LOTS_DIR.glob("*.json"):
        lot = json.loads(path.read_text(encoding="utf-8"))
        for entry in lot.get("entries", []) + lot.get("layout", []):
            if "file" in entry:
                files.add(entry["file"])
    return sorted(files)


def data_offset(raw: bytes) -> int:
    """Where the object data starts, per the serialized file header."""
    return int.from_bytes(raw[12:16], "big")


def diff_kind(before: bytes, after: bytes) -> tuple[str, bool]:
    """Classify the difference between vanilla bytes and re-serialized bytes.

    Byte equality is not the bar. Unity's own builds pad the metadata region up
    to a 4096-byte boundary; UnityPy packs it tight, which shifts every object
    and shrinks the file. The engine reads the start of the data from the header,
    so that repacking is legitimate — what matters is whether the objects survive,
    which the semantic comparison below decides.
    """
    if before == after:
        return "identique", True

    pad = len(after) - len(before)
    tail_only = (
        before[:4] == after[:4]
        and before[8 : len(before)] == after[8 : len(before)]
        and pad >= 0
        and after[len(before) :] == b"\x00" * pad
    )
    if tail_only and pad < 8:
        return f"padding align 8 (+{pad} octets)", True

    off_before, off_after = data_offset(before), data_offset(after)
    if off_before != off_after:
        return (
            f"entete retassee, debut des donnees {off_before} -> {off_after} "
            f"({pad:+d} octets)",
            True,
        )
    return "DIVERGENCE INATTENDUE", False


def read_state(path) -> dict:
    """Semantic fingerprint of a serialized file.

    Stronger than comparing bytes: every object must still be listed with the
    same identity, every typetree must still parse, and every text must read
    back unchanged.
    """
    env = load_env(path)
    try:
        shape = sorted((obj.path_id, obj.type.name) for obj in env.objects)
        unreadable = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                obj.read_typetree()
            except Exception as exc:  # noqa: BLE001 - on veut la raison exacte
                unreadable.append((obj.path_id, type(exc).__name__))
        texts = {obj.path_id: tree["m_text"] for obj, tree in iter_texts(env)}
        return {"shape": shape, "texts": texts, "unreadable": unreadable}
    finally:
        close_env(env)


def roundtrip(rel: str) -> dict:
    src = vanilla_path(rel)
    before = src.read_bytes()
    state_before = read_state(src)

    env = load_env(src)
    try:
        after = env.file.save()
    finally:
        close_env(env)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / rel.rsplit("/", 1)[-1]
    out.write_bytes(after)

    # Re-read next to its siblings so m_Script pointers still resolve.
    probe = src.with_name(src.name + ".__roundtrip")
    try:
        probe.write_bytes(after)
        state_after = read_state(probe)
    finally:
        probe.unlink(missing_ok=True)

    kind, acceptable = diff_kind(before, after)
    return {
        "rel": rel,
        "kind": kind,
        "acceptable": acceptable,
        "objects_before": len(state_before["shape"]),
        "objects_after": len(state_after["shape"]),
        "shape_equal": state_before["shape"] == state_after["shape"],
        "texts_before": len(state_before["texts"]),
        "texts_after": len(state_after["texts"]),
        "texts_equal": state_before["texts"] == state_after["texts"],
        "broke_reading": [
            pid for pid, _ in state_after["unreadable"]
            if pid not in {p for p, _ in state_before["unreadable"]}
        ],
        "out": out,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Porte de validation round-trip UnityPy")
    ap.add_argument("targets", nargs="*", default=None, help="Chemins relatifs a tester")
    ap.add_argument(
        "--install",
        action="store_true",
        help="Copier les fichiers re-serialises dans le jeu pour smoke test",
    )
    ap.add_argument("--restore", action="store_true", help="Remettre le vanilla dans le jeu")
    args = ap.parse_args()

    targets = args.targets or patched_files()

    if args.restore:
        restore(targets)
        return

    results = [roundtrip(rel) for rel in targets]

    ok = True
    for r in results:
        good = (
            r["acceptable"]
            and r["shape_equal"]
            and r["texts_equal"]
            and not r["broke_reading"]
        )
        ok = ok and good
        print(
            f"[{'OK ' if good else 'KO '}] {r['rel']}\n"
            f"      octets : {r['kind']}\n"
            f"      objets : {r['objects_before']} -> {r['objects_after']} "
            f"({'identiques' if r['shape_equal'] else 'IDENTITES DIVERGENTES'})\n"
            f"      textes : {r['texts_before']} -> {r['texts_after']} "
            f"({'identiques' if r['texts_equal'] else 'DIVERGENTS'})"
        )
        if r["broke_reading"]:
            print(f"      LECTURE CASSEE sur {len(r['broke_reading'])} objets: {r['broke_reading'][:8]}")

    if not ok:
        raise SystemExit("\nRound-trip casse: ne pas installer, rester sur le patch binaire.")

    if args.install:
        for r in results:
            shutil.copy2(r["out"], game_root() / r["rel"])
            print(f"Installe {r['rel']}")
        print(
            "\nSmoke test: menu, options, lancer une nuit, ouvrir le PC.\n"
            "Retour arriere: python scripts/roundtrip_test.py --restore"
        )
    else:
        print(f"\nFichiers dans {OUT_DIR}. Relancer avec --install pour le smoke test.")


if __name__ == "__main__":
    main()
