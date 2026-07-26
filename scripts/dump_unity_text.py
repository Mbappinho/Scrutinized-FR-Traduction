# -*- coding: utf-8 -*-
"""
Inventory every TextMeshPro string in the Unity serialized files.

Replaces the heuristic ASCII scan of scan_unity_ui_strings.py: objects are read
through generated typetrees, so each entry carries a stable (file, path_id)
address and its scene hierarchy path, which is what tells a translator whether
"Records" is an app tab or a report field.

Reads from the vanilla store by default so the inventory always describes EN.
"""
from __future__ import annotations

import argparse
import csv
import json

from game_paths import ROOT, game_root
from unity_env import TEXT_FIELD, close_env, load_env
from vanilla import load_manifest, vanilla_path

OUT_DIR = ROOT / "source" / "phase1"
OUT_JSON = OUT_DIR / "tmp_text_inventory.json"
OUT_CSV = OUT_DIR / "tmp_text_inventory.csv"

TRANSFORM_TYPES = {"Transform", "RectTransform"}
MAX_DEPTH = 12

# Field names that hold identifiers, assets or settings rather than UI copy.
FIELD_BLOCKLIST = (
    "guid",
    "shader",
    "font",
    "material",
    "path",
    "version",
    "assembly",
    "namespace",
    "classname",
    "sequence",
    "tag",
    "url",
    "scene",
    "m_name",
    "animationtrigger",
    "persistentcall",
    "methodname",
)
FIELD_EXACT_BLOCKLIST = {
    "id",
    "m_CancelButton",
    "m_SubmitButton",
    "m_HorizontalAxis",
    "m_VerticalAxis",
}


def is_texty(value: str) -> bool:
    s = value.strip()
    if len(s) < 2 or len(s) > 5000:
        return False
    if not any(c.isalpha() for c in s):
        return False
    if len(s) == 32 and all(c in "0123456789abcdef" for c in s.lower()):
        return False
    return True


def walk_strings(node, prefix=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{prefix}[{i}]")
    elif isinstance(node, str):
        yield prefix, node


def _tree(obj):
    try:
        return obj.read_typetree()
    except Exception:
        return None


def hierarchy_path(tree: dict, by_id: dict) -> str:
    """Rebuild 'Canvas/MainMenu/PlayButton/Text' from the transform chain."""
    go_ptr = tree.get("m_GameObject") or {}
    if go_ptr.get("m_FileID") != 0:
        return ""
    names: list[str] = []
    go = by_id.get(go_ptr.get("m_PathID"))
    depth = 0
    while go is not None and depth < MAX_DEPTH:
        depth += 1
        go_tree = _tree(go)
        if not go_tree:
            break
        names.append(go_tree.get("m_Name") or "?")

        transform = None
        for comp in go_tree.get("m_Component") or []:
            ptr = comp.get("component") if isinstance(comp, dict) else None
            if not ptr or ptr.get("m_FileID") != 0:
                continue
            cand = by_id.get(ptr.get("m_PathID"))
            if cand is not None and cand.type.name in TRANSFORM_TYPES:
                transform = cand
                break
        if transform is None:
            break

        t_tree = _tree(transform)
        father = (t_tree or {}).get("m_Father") or {}
        if father.get("m_FileID") != 0 or not father.get("m_PathID"):
            break
        parent_t = by_id.get(father["m_PathID"])
        if parent_t is None:
            break
        parent_tree = _tree(parent_t)
        parent_go_ptr = (parent_tree or {}).get("m_GameObject") or {}
        if parent_go_ptr.get("m_FileID") != 0:
            break
        go = by_id.get(parent_go_ptr.get("m_PathID"))

    return "/".join(reversed(names))


def scan_file(rel: str, use_install: bool) -> list[dict]:
    path = (game_root() / rel) if use_install else vanilla_path(rel)
    if not path.is_file():
        return []
    env = load_env(path)
    try:
        by_id = {o.path_id: o for o in env.objects}
        rows = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            # TMP font assets are full of strings, none of them player facing.
            if "m_FaceInfo" in tree:
                continue

            context = hierarchy_path(tree, by_id) or (tree.get("m_Name") or "")
            for field, value in walk_strings(tree):
                low = field.lower()
                if field in FIELD_EXACT_BLOCKLIST:
                    continue
                if field != TEXT_FIELD and any(b in low for b in FIELD_BLOCKLIST):
                    continue
                if not is_texty(value):
                    continue
                rows.append(
                    {
                        "file": rel,
                        "path_id": obj.path_id,
                        "field": field,
                        "context": context,
                        "text": value,
                    }
                )
        rows.sort(key=lambda r: (r["path_id"], r["field"]))
        return rows
    finally:
        close_env(env)


def main() -> None:
    ap = argparse.ArgumentParser(description="Inventaire des textes TMP par PathID")
    ap.add_argument(
        "--install",
        action="store_true",
        help="Lire l'install Steam au lieu du store vanilla (pour verifier un patch)",
    )
    ap.add_argument("--files", nargs="*", help="Restreindre a certains fichiers relatifs")
    args = ap.parse_args()

    rels = args.files or list(load_manifest()["files"])
    rels = [r for r in rels if not r.endswith("browser_assets")]

    all_rows: list[dict] = []
    for rel in rels:
        rows = scan_file(rel, args.install)
        if rows:
            tmp = sum(1 for r in rows if r["field"] == TEXT_FIELD)
            print(f"{len(rows):5d}  {rel}  (m_text: {tmp})")
        all_rows.extend(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "source": "install" if args.install else "vanilla",
                "count": len(all_rows),
                "entries": all_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "path_id", "field", "context", "text"])
        w.writeheader()
        w.writerows(all_rows)

    unique = len({r["text"] for r in all_rows})
    print(f"\n{len(all_rows)} textes ({unique} uniques)")
    print(f"  {OUT_JSON}")
    print(f"  {OUT_CSV}")


if __name__ == "__main__":
    main()
