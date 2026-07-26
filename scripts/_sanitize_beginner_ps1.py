# -*- coding: utf-8 -*-
"""Sanitize beginner PowerShell scripts for Windows PowerShell 5.1."""
from pathlib import Path

REPL = {
    "\u2014": "-",
    "\u2013": "-",
    "\u2019": "'",
    "\u2018": "'",
    "\u00e9": "e",
    "\u00e8": "e",
    "\u00ea": "e",
    "\u00e0": "a",
    "\u00f9": "u",
    "\u00ee": "i",
    "\u00f4": "o",
    "\u00e7": "c",
    "\u00c9": "E",
    "\u00c8": "E",
    "\u00c0": "A",
}

FILES = [
    "beginner_common.ps1",
    "install_fr_beginner.ps1",
    "uninstall_fr_beginner.ps1",
    "build_beginner_pack.ps1",
]


def main() -> None:
    root = Path(__file__).resolve().parent
    for name in FILES:
        path = root / name
        text = path.read_text(encoding="utf-8-sig")
        for src, dst in REPL.items():
            text = text.replace(src, dst)
        # Extra safety: avoid apostrophe inside double-quoted strings that break
        # if encoding is misread — rewrite the known fragile line.
        text = text.replace(
            'Write-Host "Backup EN deja present (reinstall FR) - on ne l\'ecrase pas."',
            'Write-Host ("Backup EN deja present (reinstall FR) - on ne l\'ecrase pas.")',
        )
        remaining = [(i, ch) for i, ch in enumerate(text) if ord(ch) > 127]
        if remaining:
            for i, ch in remaining[:20]:
                line = text.count("\n", 0, i) + 1
                print(f"{name}: U+{ord(ch):04X} line {line}")
            raise SystemExit(f"Non-ASCII remains in {name}")
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        print(f"OK {name} (UTF-8 BOM, ASCII-only strings)")


if __name__ == "__main__":
    main()
