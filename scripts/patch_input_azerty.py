# -*- coding: utf-8 -*-
"""
Remap Scrutinized movement keys from QWERTY (WASD) to AZERTY (ZQSD).

Patches InputManager inside Scrutinized_Data/globalgamemanagers:
  Horizontal.altNegativeButton : a -> q
  Vertical.altPositiveButton   : w -> z

Always starts from the vanilla store so patches never stack.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from game_paths import ROOT, game_root
from unity_env import close_env, load_env
from vanilla import restore, sha256, vanilla_path

REL = "Scrutinized_Data/globalgamemanagers"
REPORT = ROOT / "build" / "input_azerty_report.json"

# Vanilla QWERTY values we expect before remap (Steam-update guard).
EXPECTED = {
    "Horizontal": {"altNegativeButton": "a", "altPositiveButton": "d"},
    "Vertical": {"altNegativeButton": "s", "altPositiveButton": "w"},
}

# Target AZERTY physical positions (= old WASD finger positions).
TARGET = {
    "Horizontal": {"altNegativeButton": "q", "altPositiveButton": "d"},
    "Vertical": {"altNegativeButton": "s", "altPositiveButton": "z"},
}


def _input_manager(env):
    for obj in env.objects:
        if obj.type.name == "InputManager":
            return obj
    raise SystemExit(f"{REL}: InputManager introuvable")


def _axes_by_name(tree: dict) -> dict[str, dict]:
    out = {}
    for axis in tree.get("m_Axes") or []:
        name = axis.get("m_Name")
        if name:
            out[name] = axis
    return out


def _check_expected(axes: dict[str, dict], expect: dict) -> None:
    for name, fields in expect.items():
        axis = axes.get(name)
        if axis is None:
            raise SystemExit(f"{REL}: axe {name!r} manquant (MAJ Steam ?)")
        for field, value in fields.items():
            got = axis.get(field)
            if got != value:
                raise SystemExit(
                    f"{REL}: {name}.{field} inattendu.\n"
                    f"  attendu : {value!r}\n"
                    f"  lu      : {got!r}\n"
                    "  -> InputManager perime ou deja patche, relancer depuis vanilla."
                )


def apply(dry_run: bool) -> None:
    src = vanilla_path(REL)
    if not src.is_file():
        raise SystemExit(f"Vanilla manquant pour {REL}. Lancer: python scripts/vanilla.py --init")

    env = load_env(src)
    try:
        obj = _input_manager(env)
        tree = obj.read_typetree()
        axes = _axes_by_name(tree)
        _check_expected(axes, EXPECTED)

        changes = []
        for name, fields in TARGET.items():
            axis = axes[name]
            for field, new_val in fields.items():
                old = axis.get(field)
                if old == new_val:
                    continue
                axis[field] = new_val
                changes.append({"axis": name, "field": field, "from": old, "to": new_val})

        for c in changes:
            print(f"  {c['axis']}.{c['field']}: {c['from']!r} -> {c['to']!r}")

        if not changes:
            print("Rien a changer (deja ZQSD ?).")

        obj.save_typetree(tree)
        data = env.file.save()
        close_env(env)
        env = None

        if dry_run:
            print("Dry-run OK, aucune ecriture.")
            return

        dest = game_root() / REL
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

        report = {
            "when": datetime.now().isoformat(timespec="seconds"),
            "file": REL,
            "sha256_vanilla": sha256(src),
            "sha256_patched": sha256(dest),
            "changes": changes,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Ecrit {REL} ({dest.stat().st_size} octets). Rapport: {REPORT}")
    finally:
        if env is not None:
            close_env(env)


def verify() -> None:
    dest = game_root() / REL
    env = load_env(dest)
    try:
        axes = _axes_by_name(_input_manager(env).read_typetree())
        _check_expected(axes, TARGET)
        print(f"OK: InputManager AZERTY (ZQSD) dans {REL}")
    finally:
        close_env(env)


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch InputManager WASD -> ZQSD (AZERTY)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    if args.restore:
        restore([REL])
        return
    if args.verify:
        verify()
        return
    apply(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
