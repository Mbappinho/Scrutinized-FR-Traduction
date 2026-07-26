# -*- coding: utf-8 -*-
"""
Machine-translate p4_*.json lots EN -> FR (deep-translator / Google).

Preserves \\r\\n. Applies glossary post-fixes for recurring legal/game terms.
Re-runnable: skips entries where fr already differs from en.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from game_paths import ROOT

LOTS_DIR = ROOT / "work" / "lots"

# Applied after MT on the French text (literal phrase swaps).
POST_FIX = [
    (r"ordonnance de ne pas faire", "ordonnance de protection"),
    (r"ordonnance restrictive", "ordonnance de protection"),
    (r"ordre de restriction", "ordonnance de protection"),
    (r"\bB\.O\.L\.O\b", "B.O.L.O"),
    (r"\bRootKit\b", "RootKit"),
    (r"\bSCRUT\b", "SCRUT"),
    (r"\bIMEI\b", "IMEI"),
    (r"\bDOSCoin\b", "DOSCoin"),
    # Idiomes EN mal rendus par la MT
    (r"Mords-moi\s*!", "Va te faire foutre !"),
    (r"Mords moi\s*!", "Va te faire foutre !"),
    (r"ils vont probablement la rabaisser", "ils vont probablement l'euthanasier"),
    (r"je suis déprimé pour le reste", "je suis déprimée pour le reste"),
]


def translate_text(tr: GoogleTranslator, text: str) -> str:
    if not text or not text.strip():
        return text
    # Keep trailing newlines
    trailing = re.search(r"([\r\n]+)$", text)
    suffix = trailing.group(1) if trailing else ""
    core = text[: -len(suffix)] if suffix else text

    # Google limit ~4500; split on paragraphs if needed
    chunks: list[str] = []
    if len(core) < 4200:
        parts = [core]
    else:
        parts = re.split(r"(?<=\n)", core)
        # re-bucket
        buf = ""
        parts2 = []
        for p in parts:
            if len(buf) + len(p) > 4000 and buf:
                parts2.append(buf)
                buf = p
            else:
                buf += p
        if buf:
            parts2.append(buf)
        parts = parts2 or [core]

    out_parts = []
    for part in parts:
        if not part.strip():
            out_parts.append(part)
            continue
        for attempt in range(4):
            try:
                out_parts.append(tr.translate(part))
                break
            except Exception as e:
                time.sleep(1.5 * (attempt + 1))
                if attempt == 3:
                    raise RuntimeError(f"Traduction echouee: {e}") from e
        time.sleep(0.05)
    fr = "".join(out_parts) + suffix
    for pat, repl in POST_FIX:
        fr = re.sub(pat, repl, fr, flags=re.IGNORECASE)
    return fr


def translate_lot(name: str, limit: int | None = None, force: bool = False) -> None:
    path = LOTS_DIR / f"{name}.json"
    lot = json.loads(path.read_text(encoding="utf-8"))
    tr = GoogleTranslator(source="en", target="fr")
    pending = []
    for i, e in enumerate(lot["entries"]):
        if limit is not None and len(pending) >= limit:
            break
        en = e["en"]
        if not force and e.get("fr") and e["fr"] != en:
            continue
        pending.append(i)

    print(f"{name}: {len(pending)} a traduire / {len(lot['entries'])}")
    # Batch short strings with a rare delimiter to cut round-trips.
    SEP = "\n⟦§⟧\n"
    batch: list[int] = []
    batch_chars = 0
    done = 0

    def flush() -> None:
        nonlocal done, batch, batch_chars
        if not batch:
            return
        texts = [lot["entries"][i]["en"] for i in batch]
        # If any is long, translate one-by-one
        if any(len(t) > 800 for t in texts) or len(batch) == 1:
            for i in batch:
                lot["entries"][i]["fr"] = translate_text(tr, lot["entries"][i]["en"])
                done += 1
        else:
            joined = SEP.join(texts)
            fr_joined = translate_text(tr, joined)
            parts = fr_joined.split("⟦§⟧")
            parts = [p.strip("\n") for p in parts]
            if len(parts) != len(batch):
                # fallback per-item
                for i in batch:
                    lot["entries"][i]["fr"] = translate_text(tr, lot["entries"][i]["en"])
                    done += 1
            else:
                for i, fr in zip(batch, parts):
                    # restore trailing newlines from EN
                    en = lot["entries"][i]["en"]
                    trailing = re.search(r"([\r\n]+)$", en)
                    lot["entries"][i]["fr"] = fr + (trailing.group(1) if trailing else "")
                    done += 1
        batch = []
        batch_chars = 0
        if done % 50 < 20:
            path.write_text(
                json.dumps(lot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"  {name}: {done}/{len(pending)} …")

    for i in pending:
        en = lot["entries"][i]["en"]
        if batch_chars + len(en) > 3500 or len(batch) >= 40:
            flush()
        batch.append(i)
        batch_chars += len(en) + len(SEP)
    flush()
    path.write_text(json.dumps(lot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: {done} entrees traduites -> {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lot", action="append", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    for name in args.lot:
        translate_lot(name, limit=args.limit, force=args.force)


if __name__ == "__main__":
    main()
