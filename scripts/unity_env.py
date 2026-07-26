# -*- coding: utf-8 -*-
"""
Shared UnityPy environment for Scrutinized.

The player build ships almost no MonoBehaviour typetrees (3 of 214 in level1),
so they are regenerated from the Mono assemblies in Scrutinized_Data/Managed
via TypeTreeGeneratorAPI. Loading the 116 DLLs takes a moment, hence the cache.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

from game_paths import managed_dir

UNITY_VERSION = "2019.4.7f1"
TEXT_FIELD = "m_text"
TRANSFORM_TYPES = {"RectTransform", "Transform"}


@lru_cache(maxsize=1)
def get_generator() -> TypeTreeGenerator:
    gen = TypeTreeGenerator(UNITY_VERSION)
    gen.load_local_dll_folder(str(managed_dir()))
    return gen


def load_env(path: Path):
    env = UnityPy.load(str(path))
    env.typetree_generator = get_generator()
    return env


def close_env(env) -> None:
    """Release the file handles UnityPy keeps on the asset and its dependencies."""
    candidates = list(getattr(env, "files", {}).values())
    candidates.append(getattr(env, "file", None))
    for f in candidates:
        reader = getattr(f, "reader", None)
        dispose = getattr(reader, "dispose", None)
        if dispose:
            try:
                dispose()
            except Exception:
                pass


def iter_texts(env):
    """Yield (obj, tree) for every MonoBehaviour carrying a non-empty m_text."""
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        text = tree.get(TEXT_FIELD)
        if isinstance(text, str) and text.strip():
            yield obj, tree


def rect_transform(obj, by_id):
    """RectTransform sitting on the same GameObject as obj.

    Lots address text components, but resizing happens on the transform, so the
    two have to be linked through their shared GameObject.
    """
    if obj.type.name in TRANSFORM_TYPES:
        return obj
    go_ptr = (obj.read_typetree().get("m_GameObject") or {}).get("m_PathID")
    go = by_id.get(go_ptr)
    if go is None:
        return None
    for comp in go.read_typetree().get("m_Component") or []:
        cand = by_id.get(comp["component"]["m_PathID"])
        if cand is not None and cand.type.name in TRANSFORM_TYPES:
            return cand
    return None


CANVAS_WIDTH = 1920.0


def rect_width(rt_obj, by_id, depth: int = 0, overrides: dict | None = None) -> float:
    """Rendered width of a RectTransform.

    A stretched rect stores edge offsets in m_SizeDelta rather than a size, so
    its width only exists relative to its parent and the chain has to be walked
    up to the canvas. `overrides` maps a rect path_id to a width not yet written
    to the file, so a pending resize is reflected in its stretched children.
    """
    overrides = overrides or {}
    if rt_obj.path_id in overrides:
        return overrides[rt_obj.path_id]
    rt = rt_obj.read_typetree()
    if "m_AnchorMin" not in rt:
        return CANVAS_WIDTH  # plain Transform above the canvas
    a_min, a_max = rt["m_AnchorMin"]["x"], rt["m_AnchorMax"]["x"]
    size = rt["m_SizeDelta"]["x"]
    if a_min == a_max or depth > 12:
        return size
    father = by_id.get((rt.get("m_Father") or {}).get("m_PathID"))
    parent_width = (
        rect_width(father, by_id, depth + 1, overrides) if father else CANVAS_WIDTH
    )
    return (a_max - a_min) * parent_width + size


def size_delta_for(rt_obj, by_id, width: float) -> float:
    """m_SizeDelta.x that yields the requested rendered width."""
    rt = rt_obj.read_typetree()
    a_min, a_max = rt["m_AnchorMin"]["x"], rt["m_AnchorMax"]["x"]
    if a_min == a_max:
        return float(width)
    father = by_id.get((rt.get("m_Father") or {}).get("m_PathID"))
    parent_width = rect_width(father, by_id) if father else CANVAS_WIDTH
    return float(width) - (a_max - a_min) * parent_width


def _split(field: str) -> list[str | int]:
    parts: list[str | int] = []
    for chunk in field.split("."):
        while "[" in chunk:
            head, _, rest = chunk.partition("[")
            idx, _, chunk = rest.partition("]")
            if head:
                parts.append(head)
            parts.append(int(idx))
        if chunk:
            parts.append(chunk)
    return parts


def get_field(tree: dict, field: str):
    """Read a possibly nested field, e.g. 'TipDesc' or 'entries[2].label'."""
    node = tree
    for part in _split(field):
        node = node[part]
    return node


def set_field(tree: dict, field: str, value) -> None:
    parts = _split(field)
    node = tree
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
