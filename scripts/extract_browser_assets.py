# -*- coding: utf-8 -*-
"""
Extract ZFBrowser Resources/browser_assets (zfbRes_v1) for Phase 0.

Findings:
- Directory index near start lists virtual paths (/Foundation.css, /Tutorial.html, …).
- A ZIP central directory / EOCD sits near ~61.5MB (many Tutorial/*.png names).
- Plaintext CSS+HTML are stored contiguously just after the EOCD (Foundation.css
  size matches index size field 0x813 = 2067).
"""
from __future__ import annotations

import csv
import json
import re
import struct
from pathlib import Path

from game_paths import ROOT, browser_assets_path

HTML_RE = re.compile(br"<!DOCTYPE html>\s*<html[^>]*>.*?</html>", re.S | re.I)
HTML_TEXT_RE = re.compile(r">([^<>{}]{3,240})<")
SKIP_TEXT_RE = re.compile(r"^[\s\d\-_/\\|.,:;]+$")
PATH_RE = re.compile(
    rb"/[A-Za-z0-9_./\-]+\.(?:html|css|js|png|jpg|jpeg|gif|svg|json|txt|xml|zip)"
)
PNG_NAME_RE = re.compile(rb"Tutorial/[A-Za-z0-9_ ./\-]+\.png")


def parse_index_paths(data: bytes) -> list[dict]:
    """Walk the zfbRes index; record paths + flag + (offset, unk, size) when valid."""
    if not data or data[0] > 32:
        return []
    pos = 1 + data[0]
    if pos < len(data) and data[pos : pos + 1] == b";":
        pos += 1
    entries: list[dict] = []

    def try_path_at(p: int):
        if p < len(data):
            ln = data[p]
            if 1 <= ln <= 200 and p + 1 + ln <= len(data):
                cand = data[p + 1 : p + 1 + ln]
                if cand.startswith(b"/") and all(32 <= c < 127 for c in cand):
                    return "u8", ln, cand.decode("ascii")
        if p + 4 < len(data):
            be = struct.unpack_from(">I", data, p)[0]
            if 1 <= be <= 200 and p + 4 + be <= len(data):
                cand = data[p + 4 : p + 4 + be]
                if cand.startswith(b"/") and all(32 <= c < 127 for c in cand):
                    return "u32be", be, cand.decode("ascii")
        return None

    first = True
    while len(entries) < 500 and pos < min(len(data), 500_000):
        r = try_path_at(pos)
        if not r:
            break
        kind, ln, path = r
        pos = pos + (4 if kind == "u32be" else 1) + ln
        flag = data[pos]
        pos += 1
        ent: dict = {
            "path": path,
            "flag_chr": chr(flag) if 32 <= flag < 127 else hex(flag),
        }
        if first or path.endswith(".zip"):
            gap = None
            for g in range(0, 64):
                if try_path_at(pos + g):
                    gap = g
                    break
            ent["meta_gap"] = gap
            if gap is None:
                entries.append(ent)
                break
            # zip root meta ends with LE pool/base offset (last 4 of gap)
            if gap >= 4:
                ent["pool_hint"] = struct.unpack_from("<I", data, pos + gap - 4)[0]
            pos += gap
            first = False
            entries.append(ent)
            continue
        # leaf: try u32 offset + u32 zero + u32 size (12) OR offset + u16 + u32 (10)
        if pos + 12 <= len(data):
            a, b, c = struct.unpack_from("<III", data, pos)
            # Prefer layout where middle is 0 and size is small
            if b == 0 and 0 < c < 5_000_000 and a < len(data):
                ent.update({"offset": a, "unk": b, "size": c})
                pos += 12
            else:
                a2, u2, c2 = struct.unpack_from("<IHI", data, pos)
                # Detect misaligned size (high byte junk): if c2 huge, use bytes at +6 as u16/u32
                size16 = struct.unpack_from("<H", data, pos + 6)[0]
                if 0 < size16 < 500_000 and a2 < len(data):
                    ent.update({"offset": a2, "unk": u2, "size": size16, "layout": "IHI_size16_at_+6"})
                    # advance: offset(4)+pad(2)+size(2)+pad(2) = 10, if next is path len
                    pos += 10
                else:
                    ent.update({"offset": a, "unk": b, "size": c, "layout": "III_raw"})
                    pos += 12
        entries.append(ent)
    return entries


def extract_plaintext_web(data: bytes, files_out: Path) -> list[dict]:
    files_out.mkdir(parents=True, exist_ok=True)
    htmls: list[dict] = []
    for i, m in enumerate(HTML_RE.finditer(data)):
        raw = m.group(0)
        title_m = re.search(br"<title>([^<]+)</title>", raw, re.I)
        title = title_m.group(1).decode("utf-8", "replace").strip() if title_m else f"html_{i}"
        # Disambiguate duplicate titles (Tutorial vs Controls)
        if i == 0:
            fname = "Tutorial.html"
        elif b"Left Click" in raw or b"controls" in raw.lower():
            fname = "TutorialControls.html"
        else:
            fname = f"{re.sub(r'[^\w\-]+', '_', title)}_{i}.html"
        (files_out / fname).write_bytes(raw)
        htmls.append(
            {
                "offset": m.start(),
                "file": fname,
                "chars": len(raw),
                "title": title,
            }
        )

    if htmls:
        start = htmls[0]["offset"]
        i = start - 1
        while i > 0 and (data[i] in b"\r\n\t" or 32 <= data[i] < 127):
            i -= 1
            if start - i > 300_000:
                break
        css = data[i + 1 : start]
        if b"{" in css and len(css) > 50:
            (files_out / "Foundation.css").write_bytes(css)
            htmls.append(
                {
                    "offset": i + 1,
                    "file": "Foundation.css",
                    "chars": len(css),
                    "title": "Foundation.css",
                }
            )
    return htmls


def harvest_html_strings(files_out: Path) -> list[dict]:
    rows: list[dict] = []
    for html in files_out.glob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        for m in HTML_TEXT_RE.finditer(text):
            s = " ".join(m.group(1).split())
            if len(s) < 3 or SKIP_TEXT_RE.match(s) or s.startswith("http"):
                continue
            rows.append({"source": "browser_assets", "file": html.name, "text": s})
    return rows


def main() -> None:
    src = browser_assets_path()
    out = ROOT / "source" / "phase0" / "browser_assets"
    files_out = out / "files"
    data = src.read_bytes()

    index_paths = sorted({m.group(0).decode("ascii") for m in PATH_RE.finditer(data[:2_000_000])})
    entries = parse_index_paths(data)
    extracted = extract_plaintext_web(data, files_out)
    html_rows = harvest_html_strings(files_out)
    png_names = sorted({m.group(0).decode("ascii", "replace") for m in PNG_NAME_RE.finditer(data)})
    eocd = data.rfind(b"PK\x05\x06")
    first_pk = data.find(b"PK\x03\x04")

    summary = {
        "source_path": str(src),
        "size_bytes": len(data),
        "magic": data[1 : 1 + data[0]].decode("ascii", "replace"),
        "index_paths": index_paths,
        "index_entries": entries,
        "extracted": extracted,
        "html_string_rows": len(html_rows),
        "tutorial_png_names_sample": png_names[:60],
        "tutorial_png_count": len(png_names),
        "zip_eocd_offset": eocd,
        "zip_first_local_offset": first_pk,
        "note": (
            "Plaintext Foundation.css + Tutorial HTML sit after ZIP EOCD. "
            "Index size for Foundation.css matches plaintext CSS length. "
            "Full ZIP extract may fail (prepended zfb index); PNG names recovered from CD."
        ),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "index_paths.txt").write_text("\n".join(index_paths) + "\n", encoding="utf-8")
    (out / "tutorial_png_names.txt").write_text("\n".join(png_names) + "\n", encoding="utf-8")
    with (out / "html_strings.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "file", "text"])
        w.writeheader()
        w.writerows(html_rows)

    print(
        f"entries={len(entries)} extracted={len(extracted)} "
        f"html_rows={len(html_rows)} png_names={len(png_names)}"
    )
    for e in extracted:
        print(f"  {e['file']} offset={e['offset']} chars={e['chars']}")


if __name__ == "__main__":
    main()
