# -*- coding: utf-8 -*-
"""
Check every translated label actually fits the box it is rendered in.

What breaks in this game is not width, it is line count. Word wrapping is on for
almost every TextMeshPro component, so a label wider than its box does not spill
quietly: it wraps. In a UI built from fixed-height rows that means the label
eats the row below (QUITTER rendered as QUIT / TER, or the colon of
"Sous-titres :" landing on its own line).

So the model here is: lay the text out with real glyph advances from the TMP
atlases, count how many lines it needs, and compare with how many lines the box
can show. A box only tall enough for one line must never need two.

Severities:
  CASSE      one-line box forced onto several lines, or a non-wrapping label
             pushed outside the mask that clips it. Always a visible defect.
  A VERIFIER multi-line box needing more lines than it shows. Often fine, since
             these usually sit in a ScrollRect, but worth a look.
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache

from game_paths import ROOT
from text_render import rendered
from unity_env import close_env, load_env, rect_transform, rect_width
from vanilla import load_manifest, vanilla_path

LOTS_DIR = ROOT / "work" / "lots"
FONT_CACHE = ROOT / "build" / "font_metrics.json"
BREAK_AFTER = " -/\u2013\u2014"
# TMP FontStyles bits
BOLD, ITALIC, UPPERCASE, SMALLCAPS = 1, 2, 16, 32


@lru_cache(maxsize=1)
def font_metrics() -> dict:
    """{"file|path_id": metrics} for every TMP font asset in the vanilla store.

    Scanning every file is slow, so the result is cached on disk. Delete
    build/font_metrics.json after a Steam update.
    """
    if FONT_CACHE.is_file():
        return json.loads(FONT_CACHE.read_text(encoding="utf-8"))

    out = {}
    for rel in sorted(load_manifest()["files"]):
        path = vanilla_path(rel)
        if not path.is_file() or "browser_assets" in rel:
            continue
        env = load_env(path)
        try:
            for obj in env.objects:
                if obj.type.name != "MonoBehaviour":
                    continue
                try:
                    tree = obj.read_typetree()
                except Exception:
                    continue
                if "m_FaceInfo" not in tree or "m_GlyphTable" not in tree:
                    continue
                by_glyph = {
                    g["m_Index"]: g["m_Metrics"]["m_HorizontalAdvance"]
                    for g in tree.get("m_GlyphTable") or []
                }
                face = tree["m_FaceInfo"]
                out[f"{rel.rsplit('/', 1)[-1]}|{obj.path_id}"] = {
                    "name": tree.get("m_Name"),
                    "point_size": face.get("m_PointSize") or 1,
                    "face_scale": face.get("m_Scale") or 1.0,
                    "line_height": face.get("m_LineHeight") or face.get("m_PointSize") or 1,
                    "bold_spacing": tree.get("boldSpacing") or 0.0,
                    "spacing_offset": tree.get("normalSpacingOffset") or 0.0,
                    "advances": {
                        str(c["m_Unicode"]): by_glyph.get(c["m_GlyphIndex"], 0.0)
                        for c in tree.get("m_CharacterTable") or []
                    },
                }
        finally:
            close_env(env)

    FONT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    FONT_CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


def resolve_font(obj, tree, rel: str):
    """A PPtr with m_FileID 0 points inside the same file; anything else indexes
    the externals table. Matching on path_id alone would collide across files."""
    ptr = tree.get("m_fontAsset") or {}
    file_id, path_id = ptr.get("m_FileID"), ptr.get("m_PathID")
    if not path_id:
        return None
    if file_id == 0:
        name = rel.rsplit("/", 1)[-1]
    else:
        externals = obj.assets_file.externals
        if file_id - 1 >= len(externals):
            return None
        name = externals[file_id - 1].path.rsplit("/", 1)[-1]
    return font_metrics().get(f"{name}|{path_id}")


class Layout:
    """Just enough of the TMP text engine to count lines.

    The advance of a character is
      (glyphAdvance * boldMultiplier + characterSpacing + wordSpacing) * scale
    Faux bold matters a lot here: boldSpacing is 7 on every atlas of the game, so
    a bold label is 7% wider than a plain measurement suggests. Ignoring it is
    what let the wrapped e-mail subject through unnoticed.
    """

    def __init__(self, font: dict, tree: dict):
        size = tree.get("m_fontSize") or 0
        self.scale = size / font["point_size"] * font.get("face_scale", 1.0)
        self.adv = font["advances"]
        self.fallback = self.adv.get(str(ord("M")), 50.0)
        style = int(tree.get("m_fontStyle") or 0)
        self.bold_mult = 1.0 + font.get("bold_spacing", 0.0) / 100.0 if style & BOLD else 1.0
        self.upper = bool(style & (UPPERCASE | SMALLCAPS))
        self.cs = (tree.get("m_characterSpacing") or 0.0) + font.get("spacing_offset", 0.0)
        self.ws = tree.get("m_wordSpacing") or 0.0
        self.font_size = size
        self.line_advance = (
            font["line_height"] * self.scale
            + (tree.get("m_lineSpacing") or 0.0) * size / 100.0
        )

    def prepare(self, text: str) -> str:
        return text.upper() if self.upper else text

    def char_width(self, ch: str) -> float:
        w = self.adv.get(str(ord(ch)), self.fallback) * self.bold_mult + self.cs
        if ch == " ":
            w += self.ws
        return w * self.scale

    def width(self, text: str) -> float:
        return sum(self.char_width(c) for c in self.prepare(text) if c not in "\r\n")

    def lines(self, text: str, box_width: float) -> int:
        """Greedy word wrap, falling back to character wrap for a word that
        cannot fit on a line by itself, which is how QUITTER became QUIT/TER."""
        text = self.prepare(text)
        total = 0
        for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            total += self._wrap(paragraph, box_width)
        return max(total, 1)

    def _wrap(self, paragraph: str, box_width: float) -> int:
        if not paragraph:
            return 1
        # Split into chunks that must stay together, keeping break characters.
        chunks, current = [], ""
        for ch in paragraph:
            current += ch
            if ch in BREAK_AFTER:
                chunks.append(current)
                current = ""
        if current:
            chunks.append(current)

        lines, used = 1, 0.0
        for chunk in chunks:
            w = self.width(chunk)
            visible = self.width(chunk.rstrip(" "))
            if used > 0 and used + visible > box_width:
                lines += 1
                used = 0.0
            if visible > box_width:  # single unbreakable chunk, character wrap
                used = 0.0
                for ch in chunk:
                    cw = self.char_width(ch)
                    if used + cw > box_width and used > 0:
                        lines += 1
                        used = 0.0
                    used += cw
                continue
            used += w
        return lines


def span(rt_tree: dict, parent_width: float) -> tuple[float, float]:
    """Horizontal [left, right] of a RectTransform in parent-local pixels."""
    a_min = rt_tree["m_AnchorMin"]["x"]
    a_max = rt_tree["m_AnchorMax"]["x"]
    pos = rt_tree["m_AnchoredPosition"]["x"]
    size = rt_tree["m_SizeDelta"]["x"]
    pivot = rt_tree["m_Pivot"]["x"]
    width = (a_max - a_min) * parent_width + size
    anchor = (a_min + (a_max - a_min) * pivot) * parent_width
    left = anchor + pos - pivot * width
    return left, left + width


def rect_height(rt_obj, by_id, depth: int = 0) -> float:
    rt = rt_obj.read_typetree()
    if "m_AnchorMin" not in rt:
        return 1080.0
    a_min, a_max = rt["m_AnchorMin"]["y"], rt["m_AnchorMax"]["y"]
    size = rt["m_SizeDelta"]["y"]
    if a_min == a_max or depth > 12:
        return size
    father = by_id.get((rt.get("m_Father") or {}).get("m_PathID"))
    parent = rect_height(father, by_id, depth + 1) if father else 1080.0
    return (a_max - a_min) * parent + size


def grows_vertically(obj, by_id) -> bool:
    """A ContentSizeFitter or a ScrollRect ancestor means the box is allowed to
    become as tall as the text, so line count says nothing about breakage."""
    go = by_id.get((obj.read_typetree().get("m_GameObject") or {}).get("m_PathID"))
    if go is not None:
        for comp in go.read_typetree().get("m_Component") or []:
            cand = by_id.get(comp["component"]["m_PathID"])
            if cand is None or cand.type.name != "MonoBehaviour":
                continue
            try:
                tree = cand.read_typetree()
            except Exception:
                continue
            if "m_VerticalFit" in tree and tree["m_VerticalFit"]:
                return True

    rt = rect_transform(obj, by_id)
    for _ in range(8):
        if rt is None:
            break
        father = by_id.get((rt.read_typetree().get("m_Father") or {}).get("m_PathID"))
        if father is None:
            break
        fgo = by_id.get((father.read_typetree().get("m_GameObject") or {}).get("m_PathID"))
        if fgo is not None:
            for comp in fgo.read_typetree().get("m_Component") or []:
                cand = by_id.get(comp["component"]["m_PathID"])
                if cand is None or cand.type.name != "MonoBehaviour":
                    continue
                try:
                    tree = cand.read_typetree()
                except Exception:
                    continue
                if "m_Viewport" in tree or "m_VerticalScrollbar" in tree:
                    return True
        rt = father
    return False


def clip_width(rt_obj, by_id) -> float | None:
    """Width of the nearest ancestor that masks its children, if any."""
    rt = rt_obj
    for _ in range(8):
        father = by_id.get((rt.read_typetree().get("m_Father") or {}).get("m_PathID"))
        if father is None:
            return None
        fgo = by_id.get((father.read_typetree().get("m_GameObject") or {}).get("m_PathID"))
        if fgo is not None:
            for comp in fgo.read_typetree().get("m_Component") or []:
                cand = by_id.get(comp["component"]["m_PathID"])
                if cand is None or cand.type.name != "MonoBehaviour":
                    continue
                try:
                    tree = cand.read_typetree()
                except Exception:
                    continue
                if "m_Softness" in tree or "m_ShowMaskGraphic" in tree:
                    return rect_width(father, by_id)
        rt = father
    return None


def room_to_the_right(rt_obj, by_id, depth: int = 0) -> float | None:
    """How far the box can grow right before hitting something. A label alone in
    its button has no sibling in the way, so the limit lives further up."""
    if depth > 8:
        return None
    rt = rt_obj.read_typetree()
    if "m_AnchorMin" not in rt:
        return None
    father = by_id.get((rt.get("m_Father") or {}).get("m_PathID"))
    if father is None:
        return None
    ft = father.read_typetree()
    if "m_AnchorMin" not in ft:
        return None
    parent_width = rect_width(father, by_id)
    if parent_width <= 0:
        return None

    left, right = span(rt, parent_width)
    top = rt["m_AnchoredPosition"]["y"]
    own_height = max(rt["m_SizeDelta"]["y"], 1.0)
    blocker = None
    for ch in ft.get("m_Children") or []:
        sib = by_id.get(ch["m_PathID"])
        if sib is None or sib.path_id == rt_obj.path_id:
            continue
        st = sib.read_typetree()
        s_left, _ = span(st, parent_width)
        s_height = max(st["m_SizeDelta"]["y"], 1.0)
        if abs(st["m_AnchoredPosition"]["y"] - top) > (s_height + own_height) / 2:
            continue  # different row
        if s_left >= right:
            blocker = s_left if blocker is None else min(blocker, s_left)

    if blocker is not None:
        return blocker - right
    parent_room = room_to_the_right(father, by_id, depth + 1)
    return (parent_width - right) + (parent_room if parent_room is not None else 0.0)


def measured_in(entry: dict) -> tuple[str, int]:
    """Which component decides whether the text fits.

    Usually the one holding it. But narrative text lives in ScriptableObjects
    with no geometry of their own — the intro paragraphs sit in sharedassets5 and
    are drawn by a box in level5 — so an entry may name its display component
    explicitly through "display".
    """
    display = entry.get("display")
    if display:
        return display["file"], int(display["path_id"])
    return entry["file"], int(entry["path_id"])


def audit(entries: list[dict], widened: dict, autosize: dict) -> list[dict]:
    by_file: dict[str, list[dict]] = {}
    for e in entries:
        by_file.setdefault(measured_in(e)[0], []).append(e)

    findings = []
    for rel, items in sorted(by_file.items()):
        env = load_env(vanilla_path(rel))
        try:
            by_id = {o.path_id: o for o in env.objects}
            overrides = {}
            for (lot_rel, pid), width in widened.items():
                if lot_rel != rel or pid not in by_id:
                    continue
                rt = rect_transform(by_id[pid], by_id)
                if rt is not None:
                    overrides[rt.path_id] = width

            for e in items:
                obj = by_id.get(measured_in(e)[1])
                if obj is None:
                    continue
                for target, tree, label in render_targets(obj, by_id, e):
                    found = check_one(
                        rel, e, target, tree, label, by_id, overrides, autosize
                    )
                    if found:
                        findings.append(found)
        finally:
            close_env(env)
    return findings


def render_targets(obj, by_id, entry):
    """Where a lot entry actually ends up on screen.

    A plain m_text is drawn by its own component. Dropdown options are drawn by
    the dropdown's item and caption components, so they have to be measured
    against those boxes instead.
    """
    tree = obj.read_typetree()
    if "m_Options" in entry.get("field", "m_text"):
        for key, label in (("m_ItemText", "liste"), ("m_CaptionText", "champ")):
            target = by_id.get((tree.get(key) or {}).get("m_PathID"))
            if target is None:
                continue
            try:
                yield target, target.read_typetree(), label
            except Exception:
                continue
        return
    if "m_text" in tree:
        yield obj, tree, ""


def check_one(rel, e, obj, tree, label, by_id, overrides, autosize) -> dict | None:
    # Measure what will be written, accents folded away, not the lot's spelling.
    e = {**e, "fr": rendered(e["fr"])}
    font = resolve_font(obj, tree, rel)
    rt_obj = rect_transform(obj, by_id)
    if font is None or rt_obj is None:
        return None

    box_w = rect_width(rt_obj, by_id, overrides=overrides)
    box_h = rect_height(rt_obj, by_id)
    margin = tree.get("m_margin") or {}
    usable_w = box_w - (margin.get("x", 0.0) + margin.get("z", 0.0))
    usable_h = box_h - (margin.get("y", 0.0) + margin.get("w", 0.0))
    if usable_w <= 0:
        return None

    lay = Layout(font, tree)
    if lay.line_advance <= 0:
        return None
    shows = max(1, int(usable_h / lay.line_advance + 0.02))
    if grows_vertically(obj, by_id):
        shows = max(shows, 999)

    if tree.get("m_enableWordWrapping", 1):
        need_fr = lay.lines(e["fr"], usable_w)
        need_en = lay.lines(e["en"], usable_w)
        # Two ways to be at fault: exceeding what the box shows, and needing more
        # lines than the English did. A text the game itself already cut off is
        # not ours to answer for, but making the cut worse is.
        over = need_fr > shows and need_fr > need_en
        kind = "lignes"
        detail = f"{need_fr} lignes pour {shows} affichable(s) (EN {need_en})"
        regression = need_en <= shows
    else:
        clip = clip_width(rt_obj, by_id)
        limit = min(usable_w, clip) if clip else usable_w
        w_fr, w_en = lay.width(e["fr"]), lay.width(e["en"])
        over = w_fr > limit
        kind = "coupe"
        detail = f"{w_fr:.0f} de large pour {limit:.0f} (EN {w_en:.0f})"
        regression = w_en <= limit
    if not over:
        return None

    widest = max((lay.width(line) for line in e["fr"].split("\n")), default=0.0)

    # Auto-sizing rescues the label when shrinking enough still stays above the
    # floor, so it is not a defect.
    floor = autosize.get((e["file"], e["path_id"]))
    if floor is None and tree.get("m_enableAutoSizing"):
        floor = tree.get("m_fontSizeMin") or 0
    if floor and widest > 0 and shows == 1:
        if lay.font_size * usable_w / widest >= floor:
            return None

    return {
        "file": e["file"],
        "path_id": e["path_id"],
        # Only a regression counts as a defect: a text already exceeding its box
        # in English renders the same way in both languages, which is the game's
        # own choice rather than something the translation broke.
        "severity": "CASSE",
        "kind": kind,
        "detail": detail,
        "fr": e["fr"],
        "en": e["en"],
        "context": " ".join(filter(None, (e.get("context", ""), label))),
        "box_w": box_w,
        "usable_w": usable_w,
        "need_width": widest,
        "font_size": lay.font_size,
        "room": room_to_the_right(rt_obj, by_id),
        "regression": regression,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Controle de debordement des libelles FR")
    ap.add_argument("--all", action="store_true", help="Inclure les A VERIFIER")
    ap.add_argument("--propose", action="store_true", help="Emettre des entrees layout JSON")
    args = ap.parse_args()

    entries = []
    widened: dict[tuple[str, int], float] = {}
    autosize: dict[tuple[str, int], float] = {}
    for p in sorted(LOTS_DIR.glob("*.json")):
        lot = json.loads(p.read_text(encoding="utf-8"))
        entries.extend(e for e in lot.get("entries", []) if "file" in e and "path_id" in e)
        for it in lot.get("layout", []):
            if "file" not in it or "path_id" not in it:
                continue
            key = (it["file"], int(it["path_id"]))
            if "width" in it:
                widened[key] = float(it["width"])
            if "autosize_min" in it:
                autosize[key] = float(it["autosize_min"])

    findings = audit(entries, widened, autosize)
    broken = [f for f in findings if f["severity"] == "CASSE"]

    if args.propose:
        out = []
        for f in broken:
            need = round(f["need_width"] + 8)
            room = f["room"]
            item = {"file": f["file"], "path_id": f["path_id"], "why": f["fr"][:40]}
            if room is not None and need - f["box_w"] > room:
                # No space to grow into: shrink the glyphs instead of the box.
                item["autosize_min"] = round(
                    f["font_size"] * f["usable_w"] / f["need_width"] - 0.5
                )
                item["_manque"] = round(need - f["box_w"] - room)
            else:
                item["width"] = need
                item["_croissance"] = round(need - f["box_w"])
            item["_marge"] = None if room is None else round(room)
            out.append(item)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    shown = findings if args.all else broken
    for f in sorted(shown, key=lambda f: (f["severity"], f["file"], f["path_id"])):
        tag = "" if f["regression"] else "  (deja limite en EN)"
        print(
            f"{f['severity']:10} {f['file'].rsplit('/', 1)[-1]:22} {f['path_id']:>6}  "
            f"{f['kind']:6} {f['detail']}{tag}"
        )
        print(f"           {f['context']}")
        print(f"           {f['fr'][:70]!r}")

    print(f"\n{len(broken)} defauts visibles (CASSE).")
    if not args.all:
        rest = len(findings) - len(broken)
        if rest:
            print(f"{rest} a verifier (boites multi-lignes), relancer avec --all.")


if __name__ == "__main__":
    main()
