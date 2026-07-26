# -*- coding: utf-8 -*-
"""
Apply French string lots to Assembly-CSharp.dll via dnlib.

Unlike the Unity asset patcher, strings are addressed by their English value —
the same string may be loaded from many call sites, and the English wording is
the only stable identity across Steam updates.

Every run starts from the vanilla store, so patches never stack. Accents are
folded on write through text_render.rendered(), same as the asset pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

# CoreCLR before importing clr — the machine has runtimes but no SDK.
os.environ.setdefault("PYTHONNET_RUNTIME", "coreclr")

import clr  # noqa: E402

from game_paths import ROOT, game_root
from text_render import rendered, unrenderable
from vanilla import restore, sha256, vanilla_path

LOTS_DIR = ROOT / "work" / "lots"
DLL_REL = "Scrutinized_Data/Managed/Assembly-CSharp.dll"
DNLIB = ROOT / "tools" / "dnlib" / "pkg" / "lib" / "netstandard2.0" / "dnlib.dll"
REPORT = ROOT / "build" / "dll_patch_report.json"


def _load_dnlib():
    if not DNLIB.is_file():
        raise SystemExit(
            f"dnlib introuvable: {DNLIB}\n"
            "Telecharger le paquet NuGet dnlib dans tools/dnlib/."
        )
    clr.AddReference(str(DNLIB))
    from dnlib.DotNet import ModuleDefMD  # type: ignore
    from dnlib.DotNet.Emit import OpCodes  # type: ignore
    from dnlib.DotNet.Writer import ModuleWriterOptions  # type: ignore

    return ModuleDefMD, ModuleWriterOptions, OpCodes


def load_dll_lot(only: str | None = "p3_dll") -> list[dict]:
    paths = sorted(LOTS_DIR.glob("*.json"))
    if only:
        paths = [p for p in paths if p.stem == only]
    entries: list[dict] = []
    seen: dict[str, str] = {}
    for p in paths:
        lot = json.loads(p.read_text(encoding="utf-8"))
        for e in lot.get("entries", []):
            if "file" in e:  # Unity lot, skip
                continue
            if "en" not in e or "fr" not in e:
                raise SystemExit(f"Entree incomplete dans {p.name}: {e}")
            if e["en"] in seen:
                raise SystemExit(f"Doublon EN {e['en']!r} entre {seen[e['en']]} et {p.name}")
            seen[e["en"]] = p.name
            entries.append({**e, "lot": p.stem})
    if not entries:
        raise SystemExit("Aucun lot DLL (entrees sans champ 'file')")
    return entries


def check_renderable(entries: list[dict]) -> None:
    bad = [(e, unrenderable(e["fr"])) for e in entries]
    bad = [(e, chars) for e, chars in bad if chars]
    if bad:
        lines = "\n".join(
            f'  {e["en"]!r}: {"".join(chars)} dans {e["fr"][:50]!r}'
            for e, chars in bad[:10]
        )
        raise SystemExit(
            "Caracteres sans equivalent ASCII connu :\n"
            f"{lines}\n"
            "Completer SUBSTITUTIONS dans scripts/text_render.py."
        )


def count_ldstr(module, targets: set[str], OpCodes) -> dict[str, int]:
    counts = {t: 0 for t in targets}
    for typ in module.GetTypes():
        for method in typ.Methods:
            if not method.HasBody:
                continue
            for instr in method.Body.Instructions:
                if instr.OpCode == OpCodes.Ldstr and instr.Operand in targets:
                    counts[instr.Operand] += 1
    return counts


def replace_ldstr(module, mapping: dict[str, str], OpCodes) -> dict[str, int]:
    """Replace every ldstr operand that matches a key. Returns hit counts."""
    hits = {en: 0 for en in mapping}
    for typ in module.GetTypes():
        for method in typ.Methods:
            if not method.HasBody:
                continue
            for instr in method.Body.Instructions:
                if instr.OpCode != OpCodes.Ldstr:
                    continue
                en = instr.Operand
                if en in mapping:
                    instr.Operand = mapping[en]
                    hits[en] += 1
    return hits


# UnityEngine.KeyCode
KEYCODE_A = 97
KEYCODE_Q = 113


def patch_seccams_azerty(module, OpCodes) -> int:
    """SecCamsHook.Update: KeyCode.A (strafe left) -> KeyCode.Q for AZERTY.

    Anchored to SecCamsHook.Update only — never a global replace of ldc.i4 97.
    """
    from System import Int32, SByte  # type: ignore

    typ = next((t for t in module.Types if str(t.Name) == "SecCamsHook"), None)
    if typ is None:
        raise SystemExit("SecCamsHook introuvable dans la DLL vanilla")
    method = next((m for m in typ.Methods if str(m.Name) == "Update"), None)
    if method is None or not method.HasBody:
        raise SystemExit("SecCamsHook.Update introuvable")

    hits = 0
    for instr in method.Body.Instructions:
        if instr.OpCode not in (OpCodes.Ldc_I4, OpCodes.Ldc_I4_S):
            continue
        try:
            val = int(instr.GetLdcI4Value())
        except Exception:
            continue
        if val == KEYCODE_A:
            if instr.OpCode == OpCodes.Ldc_I4_S:
                instr.Operand = SByte(KEYCODE_Q)
            else:
                instr.Operand = Int32(KEYCODE_Q)
            hits += 1
    if hits == 0:
        raise SystemExit(
            "SecCamsHook.Update: aucun KeyCode.A (97) a patcher "
            "(deja AZERTY ou MAJ Steam ?)"
        )
    return hits


def count_seccams_key(module, keycode: int, OpCodes) -> int:
    typ = next((t for t in module.Types if str(t.Name) == "SecCamsHook"), None)
    if typ is None:
        return 0
    method = next((m for m in typ.Methods if str(m.Name) == "Update"), None)
    if method is None or not method.HasBody:
        return 0
    n = 0
    for instr in method.Body.Instructions:
        if instr.OpCode not in (OpCodes.Ldc_I4, OpCodes.Ldc_I4_S):
            continue
        try:
            if int(instr.GetLdcI4Value()) == keycode:
                n += 1
        except Exception:
            pass
    return n


def apply(dry_run: bool) -> None:
    ModuleDefMD, ModuleWriterOptions, OpCodes = _load_dnlib()
    entries = load_dll_lot()
    check_renderable(entries)

    mapping = {e["en"]: rendered(e["fr"]) for e in entries}
    # Skip no-ops (EN already equals folded FR).
    mapping = {en: fr for en, fr in mapping.items() if en != fr}

    src = vanilla_path(DLL_REL)
    if not src.is_file():
        raise SystemExit(f"Vanilla manquant pour {DLL_REL}. Lancer: python scripts/vanilla.py --init")

    module = ModuleDefMD.Load(str(src))
    try:
        before = count_ldstr(module, set(mapping), OpCodes)
        missing = [en for en, n in before.items() if n == 0]
        if missing:
            sample = "\n".join(f"  {s!r}" for s in missing[:10])
            raise SystemExit(
                "Chaines EN absentes de la DLL vanilla (MAJ Steam ?) :\n"
                f"{sample}\n"
                "Relancer scripts/scan_dll_strings.py et mettre a jour le lot."
            )

        hits = replace_ldstr(module, mapping, OpCodes)
        total_hits = sum(hits.values())
        seccams_hits = patch_seccams_azerty(module, OpCodes)

        print(f"{len(mapping)} chaines a remplacer, {total_hits} sites ldstr")
        print(f"  SecCamsHook.Update: KeyCode.A -> Q ({seccams_hits} site(s))")
        for e in entries:
            en = e["en"]
            if en not in mapping:
                continue
            fr = mapping[en]
            folded = "  (accents replies)" if fr != e["fr"] else ""
            print(f"  [{hits[en]:>2}x] {en!r} -> {fr!r}{folded}")

        if dry_run:
            print("\nDry-run OK, aucune ecriture.")
            return

        dest = game_root() / DLL_REL
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file next to dest, then replace — Mono locks the DLL
        # while the game is running.
        tmp = dest.with_suffix(".dll.__patch")
        opts = ModuleWriterOptions(module)
        module.Write(str(tmp), opts)

        # Verify the written file before installing.
        probe = ModuleDefMD.Load(str(tmp))
        try:
            fr_targets = set(mapping.values())
            fr_hits = count_ldstr(probe, fr_targets, OpCodes)
            en_left = count_ldstr(probe, set(mapping), OpCodes)
            bad_fr = [s for s in fr_targets if fr_hits.get(s, 0) == 0]
            bad_en = [s for s, n in en_left.items() if n > 0]
            if bad_fr or bad_en:
                tmp.unlink(missing_ok=True)
                raise SystemExit(
                    f"Verification ecriture ratee: FR manquants={bad_fr[:5]}, "
                    f"EN restants={bad_en[:5]}"
                )
            if count_seccams_key(probe, KEYCODE_A, OpCodes) != 0:
                tmp.unlink(missing_ok=True)
                raise SystemExit("Verification: KeyCode.A encore present dans SecCamsHook.Update")
            if count_seccams_key(probe, KEYCODE_Q, OpCodes) < 1:
                tmp.unlink(missing_ok=True)
                raise SystemExit("Verification: KeyCode.Q absent de SecCamsHook.Update")
        finally:
            probe.Dispose()

        shutil.move(str(tmp), str(dest))
        report = {
            "when": datetime.now().isoformat(timespec="seconds"),
            "dll": DLL_REL,
            "sha256_vanilla": sha256(src),
            "sha256_patched": sha256(dest),
            "size_vanilla": src.stat().st_size,
            "size_patched": dest.stat().st_size,
            "seccams_azerty": {"from": "KeyCode.A", "to": "KeyCode.Q", "hits": seccams_hits},
            "replacements": [
                {"en": e["en"], "fr": mapping[e["en"]], "hits": hits[e["en"]], "lot": e["lot"]}
                for e in entries
                if e["en"] in mapping
            ],
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nEcrit {DLL_REL} ({dest.stat().st_size} octets). Rapport: {REPORT}")
    finally:
        module.Dispose()


def verify() -> None:
    ModuleDefMD, _, OpCodes = _load_dnlib()
    entries = load_dll_lot()
    mapping = {e["en"]: rendered(e["fr"]) for e in entries}
    mapping = {en: fr for en, fr in mapping.items() if en != fr}

    dest = game_root() / DLL_REL
    module = ModuleDefMD.Load(str(dest))
    try:
        fr_hits = count_ldstr(module, set(mapping.values()), OpCodes)
        en_hits = count_ldstr(module, set(mapping), OpCodes)
        bad = 0
        for en, fr in mapping.items():
            if fr_hits.get(fr, 0) == 0:
                bad += 1
                print(f"KO FR absent: {fr!r} (depuis {en!r})")
            if en_hits.get(en, 0) > 0:
                bad += 1
                print(f"KO EN encore present ({en_hits[en]}x): {en!r}")
        a_left = count_seccams_key(module, KEYCODE_A, OpCodes)
        q_hits = count_seccams_key(module, KEYCODE_Q, OpCodes)
        if a_left:
            bad += 1
            print(f"KO SecCamsHook: KeyCode.A encore present ({a_left}x)")
        if q_hits < 1:
            bad += 1
            print("KO SecCamsHook: KeyCode.Q absent")
        if bad:
            raise SystemExit(f"{bad} ecarts.")
        print(
            f"OK: {len(mapping)} chaines FR presentes, EN absents dans {DLL_REL}; "
            f"SecCams A->Q OK"
        )
    finally:
        module.Dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch FR de Assembly-CSharp.dll")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    if args.restore:
        restore([DLL_REL])
        return
    if args.verify:
        verify()
        return
    apply(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
