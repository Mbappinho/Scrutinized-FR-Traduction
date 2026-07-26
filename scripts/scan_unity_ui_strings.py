# -*- coding: utf-8 -*-
"""Find Unity aligned ASCII strings that look like P0 UI labels."""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

from game_paths import ROOT, data_dir

FILES = [
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
    "sharedassets0.assets",
    "sharedassets1.assets",
    "sharedassets2.assets",
    "sharedassets3.assets",
    "sharedassets5.assets",
    "sharedassets7.assets",
    "sharedassets9.assets",
    "resources.assets",
]

UI_HINT = re.compile(
    r"(?i)play|quit|option|setting|menu|door|window|hide|lock|unlock|open|close|"
    r"light|flash|sit|stand|pause|resume|continue|credit|volume|music|sensitiv|"
    r"fullscreen|detective|nightmare|normal|loading|thanks|jump.?scare|interact|"
    r"closet|router|breaker|modem|camera|bed|apply|reset|cancel|confirm|back|"
    r"submit|save|load|how to|tutor"
)


def align4(n: int) -> int:
    return (n + 3) & ~3


def iter_unity_ascii_strings(blob: bytes):
    i = 0
    end = len(blob) - 8
    while i < end:
        (n,) = struct.unpack_from("<i", blob, i)
        if 2 <= n <= 120:
            data_start = i + 4
            data_end = data_start + n
            if data_end < len(blob) and blob[data_end] == 0:
                raw = blob[data_start:data_end]
                if all(32 <= b < 127 or b in (9, 10, 13) for b in raw):
                    text = raw.decode("ascii")
                    total = 4 + align4(n + 1)
                    if (" " in text or UI_HINT.search(text)) and not any(
                        x in text for x in ("BTN", "Manager", "Controller", "Script", "Unity", "http")
                    ):
                        if " " in text or text in {
                            "Options",
                            "Settings",
                            "Resume",
                            "Pause",
                            "Continue",
                            "Play",
                            "Quit",
                            "Exit",
                            "Back",
                            "Cancel",
                            "Confirm",
                            "Submit",
                            "Save",
                            "Load",
                            "Loading",
                            "Open",
                            "Close",
                            "Lock",
                            "Unlock",
                            "Hide",
                            "Apply",
                            "Reset",
                            "Credits",
                            "Detective",
                            "Nightmare",
                            "Normal",
                            "Interact",
                            "Fullscreen",
                            "Volume",
                            "Music",
                            "Sensitivity",
                        }:
                            yield {
                                "offset": i,
                                "length": n,
                                "text": text,
                                "slot_bytes": total,
                            }
                    i += total
                    continue
        i += 1


def main() -> None:
    out_dir = ROOT / "source" / "phase1" / "menus_inventory"
    out_dir.mkdir(parents=True, exist_ok=True)
    found = []
    for name in FILES:
        path = data_dir() / name
        if not path.is_file():
            continue
        print("scan", name, flush=True)
        blob = path.read_bytes()
        for s in iter_unity_ascii_strings(blob):
            if not UI_HINT.search(s["text"]):
                continue
            # skip code-ish identifiers without spaces unless exact UI words
            t = s["text"]
            if " " not in t and t not in {
                "Options",
                "Settings",
                "Resume",
                "Pause",
                "Continue",
                "Play",
                "Quit",
                "Exit",
                "Back",
                "Cancel",
                "Confirm",
                "Submit",
                "Save",
                "Load",
                "Loading",
                "Open",
                "Close",
                "Lock",
                "Unlock",
                "Hide",
                "Apply",
                "Reset",
                "Credits",
                "Detective",
                "Nightmare",
                "Normal",
                "Interact",
                "Fullscreen",
                "Volume",
                "Music",
                "Sensitivity",
            }:
                continue
            if any(x in t for x in ("BTN", "Manager", "Controller", "Script", "Unity", "http")):
                continue
            found.append({"container": name, **s})

    # dedupe by text keep all locations
    by_text: dict[str, list] = {}
    for row in found:
        by_text.setdefault(row["text"], []).append(row)

    summary = {
        "count_strings": len(by_text),
        "texts": sorted(by_text.keys(), key=str.lower),
        "locations": by_text,
    }
    (out_dir / "menus_unity_strings.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("unique", len(by_text))
    for t in summary["texts"]:
        locs = by_text[t]
        print(f"{t!r} len={locs[0]['length']} slot={locs[0]['slot_bytes']} x{len(locs)} {locs[0]['container']}")


if __name__ == "__main__":
    main()
