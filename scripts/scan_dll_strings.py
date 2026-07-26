# -*- coding: utf-8 -*-
"""
Inventory the text that lives in Assembly-CSharp.dll rather than in the assets.

This is the last pocket of English the player can see, and it is out of reach of
the UnityPy pipeline. The point of this script is not to patch anything but to
keep an honest, checkable list of what is left and why it is hard.

Two heaps matter, and the distinction decides how hard a string is to change:

- `#US`, the user string heap, holds UTF-16 literals — the messages the code
  writes into the UI. Rewriting one means rebuilding the assembly, but nothing
  else in the program depends on its content.
- `#Strings`, the metadata heap, holds identifiers, including **enum member
  names**. Hair and eye colours are displayed by turning an enum into text, so
  their English wording is a member name. Renaming it also renames what any
  ToString/Parse round trip or dictionary key sees, which can quietly break saves
  and comparisons.

CURATED is checked on every run: a string that disappears means Steam shipped an
update and this inventory needs revisiting. Same idea as the `en` guard in the
lots.
"""
from __future__ import annotations

import json
import re
import sys

from game_paths import ROOT, game_root
from vanilla import vanilla_path

REPORT = ROOT / "build" / "dll_strings.json"
DLL_REL = "Scrutinized_Data/Managed/Assembly-CSharp.dll"

# Player-visible UTF-16 literals, grouped by where they show up in game.
CURATED: dict[str, list[str]] = {
    "recherches SCRUT": [
        "No results found.",
        "NO RESULTS",
        "NO DATAAAA",
        "Invalid search parameters.",
        "Please specify at least one search parameter.",
        "Please enter a valid name.",
        "Please provide a full name or an alias.",
        "Invaid Search. Name field is empty.",
        "Invaid Search. Name is to short.",
        "Invaid Search. Please include a last name.",
        "No police record found.",
        "No recent transactions found.",
        "This person does not have a social profile.",
        "No Internet Connection.",
        " RESULT",
        " RESULTS",
    ],
    "IMEI / telephone": [
        "Invaid IMEI. Enter a valid IMEI number.",
        "Could not find an IMEI device with this name.",
        "No device is active with this IMEI number.",
    ],
    "etats de partie": [
        "NIGHT ",
        "ONE",
        "TWO",
        "THREE",
        "FOUR",
        "FIVE",
        "SIX",
        "SEVEN",
        "EIGHT",
        "NINE",
        "TEN",
        "ELEVEN",
        "TWELVE",
        "THIRTEEN",
        "FOURTEEN",
        "You Have Been Kidnapped.",
        "You Became A Statistic.",
        "Report Quota Not Met.",
        "Too Many Reports Rejected.",
        "WRONG!",
    ],
    "pensees de Luna": [
        "Finally can get to bed early for once...",
        "I should get some rest...",
    ],
    "valeurs de fiche": [
        "Male",
        "Female",
        "Unknown",
        " lbs",
    ],
    "formats de date (12h americain)": [
        "h:mm tt",
        "MM-dd h:mm tt",
        "MM-dd-yyyy h:mm tt",
        "MM/dd/yyyy h:mm tt",
    ],
}

# Values displayed by turning an enum into text. Held in the metadata heap.
ENUM_VALUES = [
    "Brown", "Blonde", "Hazel", "Blue", "Bald", "Black", "Grey", "Auburn",
    "Green", "Red", "Blond",
]

# Strings that exist but no player ever reads, grouped by why. Kept explicit
# rather than filtered by a clever regex, so the next reader can disagree.
NOT_PLAYER_FACING = {
    "greffons tiers": (
        "DOTween", "Steamworks", "SSAA", "Cinemachine", "[Singleton]", "LWRP",
        "Postprocessing", "Post Processing", "VRDevice", "SetAsAxisBased",
        "Hidden/", "DllCheck", "Packsize", "SteamAPI", "tween", "DOText",
        "(Clone)", "Requires Unity", "pointer events", "global multiplier",
        "in the scene before", "is trying to be accessed",
    ),
    "overlay Graphy": (
        "[Graphy]", "CPU: ", "GPU: ", "RAM: ", "VRAM: ", "OS: ", "Screen: ",
        "Window: ", "Graphics API: ", " cores]", " MB", "Max texture size",
        "Shader level", "Camera speed", "Controler Stats", "performance issues",
    ),
    "base SQLite / OrmLite": ("Creating Table:", "Data Source=", ";Version=", "Assembly Version"),
    "traces de debogage": (
        "Game State:", "Input State:", "State: {0}", "Player Location:",
        "Game Data Is Null", "added new post", "Debug Window", "Updating Shadow",
        "Mouse X", "Mouse Y", "Not available in VR mode",
    ),
}
THIRD_PARTY = tuple(m for markers in NOT_PLAYER_FACING.values() for m in markers)

IDENTIFIER = re.compile(r"^[\w./\\<>{}\[\]-]+$")


def literals(raw: bytes) -> set[str]:
    """UTF-16LE runs, i.e. what the #US heap looks like from the outside."""
    return {m.group().decode("utf-16-le") for m in re.finditer(rb"(?:[\x20-\x7e]\x00){3,}", raw)}


def metadata(raw: bytes) -> set[str]:
    """ASCII runs, which include the #Strings heap where identifiers live."""
    return {m.group().decode("ascii") for m in re.finditer(rb"[\x20-\x7e]{3,}", raw)}


def main() -> None:
    # Curated EN strings are checked against the vanilla store: after a FR patch
    # they are gone from the install, and that must not look like a Steam update.
    src = vanilla_path(DLL_REL)
    if not src.is_file():
        src = game_root() / DLL_REL
        print(f"(vanilla absent, lecture de l'install: {src})")
    if not src.is_file():
        raise SystemExit(f"Introuvable: {DLL_REL}")
    raw = src.read_bytes()
    lits, meta = literals(raw), metadata(raw)

    print(f"{src.name}: {len(raw)} octets, {len(lits)} litteraux UTF-16, {len(meta)} chaines ASCII")
    print(f"source: {src}\n")

    missing: list[str] = []
    total = 0
    for group, values in CURATED.items():
        print(f"--- {group}")
        for value in values:
            present = value in lits
            total += 1
            if not present:
                missing.append(value)
            print(f"   [{'ok' if present else 'DISPARU'}] {value!r}")
        print()

    print("--- valeurs d'enumeration (heap de metadonnees, pas des litteraux)")
    enums = {}
    for value in ENUM_VALUES:
        as_literal = value in lits
        as_meta = value in meta
        enums[value] = {"litteral": as_literal, "metadonnee": as_meta}
        etat = (
            "litteral" if as_literal
            else "metadonnee seule" if as_meta
            else "absent"
        )
        print(f"   {value:10} {etat}")

    known = {v for values in CURATED.values() for v in values}
    review = sorted(
        s for s in lits
        if s not in known
        and not IDENTIFIER.match(s)
        and not any(marker in s for marker in THIRD_PARTY)
        and any(c.isalpha() for c in s)
    )
    print(f"\n--- {len(review)} chaines restantes, ni repertoriees ni identifiees comme tierces")
    for s in review:
        print(f"   {s[:100]!r}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "dll": str(src),
                "octets": len(raw),
                "repertoriees": CURATED,
                "disparues": missing,
                "enumerations": enums,
                "a_examiner": review,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\n{total} chaines repertoriees, {len(missing)} disparues. Rapport: {REPORT}")
    if missing:
        print(
            "\nDes chaines repertoriees ont disparu : mise a jour Steam probable,\n"
            "reprendre docs/LIMITES_CONNUES.md."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
