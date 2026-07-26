# -*- coding: utf-8 -*-
"""
Assemble work/lots/p2_story.json from the translations and the vanilla text.

The French lives in work/p2_translations.json, keyed by the narrative labels the
game itself uses (IST1..IST19 for the intro, LES*/TES* for the Luna/Tanner
dialogue). Everything else — path_id, field, and above all the English guard
string — is read back from the inventory, because a guard typed by hand is a
guard that silently rots.

Skipped on purpose:
- DisplayName fields, which only ever hold "Luna" or "Tanner";
- SubtitleObject/SubtitleText, a "Test Mc" placeholder left in a prefab.
"""
from __future__ import annotations

import json

from game_paths import ROOT

INVENTORY = ROOT / "source" / "phase1" / "tmp_text_inventory.json"
TRANSLATIONS = ROOT / "work" / "p2_translations.json"
LOT = ROOT / "work" / "lots" / "p2_story.json"
FILES = ("sharedassets5.assets", "sharedassets9.assets")

# The intro paragraphs are ScriptableObject fields with no geometry; the box that
# decides whether they fit is the scene's subtitle label, 1720x150 for 5 lines.
# The dialogue is drawn by a prefab resized at runtime, so it cannot be declared.
INTRO_DISPLAY = {"file": "Scrutinized_Data/level5", "path_id": 94}


def main() -> None:
    raw = json.loads(INVENTORY.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else (raw.get("entries") or raw.get("items"))
    fr_by_label = {
        k: v for k, v in json.loads(TRANSLATIONS.read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }

    entries, seen = [], set()
    for item in items:
        if not item["file"].endswith(FILES):
            continue
        if item.get("field") == "DisplayName" or "Subtitle" in (item.get("context") or ""):
            continue
        label = item.get("context") or ""
        fr = fr_by_label.get(label)
        if fr is None:
            raise SystemExit(f"Traduction manquante pour {label} ({item['file']}#{item['path_id']})")
        seen.add(label)
        entry = {
            "file": item["file"],
            "path_id": item["path_id"],
            "field": item["field"],
            "context": label,
            "en": item["text"],
            "fr": fr,
        }
        if label.startswith("IST"):
            entry["display"] = INTRO_DISPLAY
        entries.append(entry)

    unused = sorted(set(fr_by_label) - seen)
    if unused:
        raise SystemExit(f"Traductions sans cible dans le vanilla : {unused}")

    def order(e):
        prefix = "".join(c for c in e["context"] if c.isalpha())
        digits = "".join(c for c in e["context"] if c.isdigit())
        return (prefix, int(digits) if digits else 0)

    entries.sort(key=order)
    LOT.write_text(
        json.dumps(
            {
                "lot": "p2_story",
                "scope": "Recit d'introduction (sharedassets5) et dialogue Luna/Tanner (sharedassets9)",
                "note": (
                    "Genere par scripts/build_p2_lot.py depuis work/p2_translations.json. "
                    "Ne pas editer a la main : editer les traductions puis regenerer."
                ),
                "entries": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    intro = sum(1 for e in entries if e["context"].startswith("IST"))
    print(f"{len(entries)} entrees ecrites dans {LOT.name} ({intro} recit, {len(entries) - intro} dialogue)")


if __name__ == "__main__":
    main()
