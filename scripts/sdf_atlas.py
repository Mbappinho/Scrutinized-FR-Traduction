# -*- coding: utf-8 -*-
"""
Generate TextMeshPro SDF atlases that match Scrutinized's encoding.

Measured on Aldrich-Regular SDF (sharedassets1):
  - Alpha8 atlas, padding 5, _GradientScale 6.0
  - Encoding: alpha = clip(0.5 + signed_distance / (2 * 6), 0, 1) * 255
  - GlyphRect is the inner content; the SDF halo extends exactly `padding`
    pixels around it into the atlas.

The generator is validated by regenerating the existing glyph set and comparing
pixel-by-pixel against the shipped atlas before any accent is added.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, zoom

# Matches the material's _GradientScale on every font of the game.
GRADIENT_SCALE = 6.0


@dataclass
class Glyph:
    char: str
    unicode: int
    bitmap: np.ndarray  # uint8, includes padding halo
    width: int  # inner content width (GlyphRect.m_Width)
    height: int
    bearing_x: float
    bearing_y: float
    advance: float
    # Packing placement, filled later.
    atlas_x: int = 0
    atlas_y: int = 0


def signed_distance_field(mask: np.ndarray, spread: float) -> np.ndarray:
    """mask: bool, True = inside glyph. Returns float distances in pixel units."""
    inside = mask
    outside = ~mask
    # distance_transform_edt of True regions = distance to nearest False.
    dist_in = distance_transform_edt(inside)
    dist_out = distance_transform_edt(outside)
    return dist_in - dist_out


def encode_sdf(distance: np.ndarray, gradient_scale: float = GRADIENT_SCALE) -> np.ndarray:
    """Map signed distance (pixels) to Alpha8 the way TMP's shader expects."""
    alpha = 0.5 + distance / (2.0 * gradient_scale)
    return (np.clip(alpha, 0.0, 1.0) * 255.0).astype(np.uint8)


def render_glyph(
    font_path: str,
    char: str,
    point_size: int,
    padding: int = 5,
    supersample: int = 8,
    gradient_scale: float = GRADIENT_SCALE,
) -> Glyph | None:
    """Rasterise one character to an SDF bitmap with a padding halo."""
    if char == " ":
        # Space has no bitmap; advance only. Caller supplies advance from FreeType.
        font = ImageFont.truetype(font_path, point_size)
        advance = float(font.getlength(char))
        return Glyph(
            char=char,
            unicode=ord(char),
            bitmap=np.zeros((0, 0), dtype=np.uint8),
            width=0,
            height=0,
            bearing_x=0.0,
            bearing_y=0.0,
            advance=advance,
        )

    hi = point_size * supersample
    font = ImageFont.truetype(font_path, hi)
    # getbbox: (left, top, right, bottom) relative to pen origin at baseline.
    bbox = font.getbbox(char)
    if bbox is None or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return None
    left, top, right, bottom = bbox
    # Extra margin at high-res so the SDF spread isn't clipped before downsample.
    margin = int(math.ceil(gradient_scale * supersample)) + supersample
    w = right - left + 2 * margin
    h = bottom - top + 2 * margin
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    # Draw so that bbox sits at (margin, margin).
    draw.text((-left + margin, -top + margin), char, font=font, fill=255)
    mask = np.array(img, dtype=np.uint8) >= 128

    dist = signed_distance_field(mask, spread=gradient_scale * supersample)
    # Downsample spatially AND convert distances to atlas-pixel units.
    dist_lo = zoom(dist, 1.0 / supersample, order=1) / float(supersample)
    sdf = encode_sdf(dist_lo, gradient_scale)

    # Crop to content + padding: find non-near-zero region, then add padding.
    ys, xs = np.where(sdf > 2)
    if len(xs) == 0:
        return None
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    # Expand to include full halo of `padding` around the solid core.
    # Core ≈ where sdf > 127.5; halo needs `padding` more.
    core = sdf > 127
    if core.any():
        cy, cx = np.where(core)
        x0 = max(0, int(cx.min()) - padding)
        x1 = min(sdf.shape[1], int(cx.max()) + 1 + padding)
        y0 = max(0, int(cy.min()) - padding)
        y1 = min(sdf.shape[0], int(cy.max()) + 1 + padding)
    crop = sdf[y0:y1, x0:x1]

    # Inner GlyphRect excludes the padding border.
    inner_w = max(0, crop.shape[1] - 2 * padding)
    inner_h = max(0, crop.shape[0] - 2 * padding)

    # Metrics at atlas point size (not supersampled).
    font_lo = ImageFont.truetype(font_path, point_size)
    bbox_lo = font_lo.getbbox(char)
    advance = float(font_lo.getlength(char))
    # PIL getbbox Y origin is unreliable across faces for bearingY (É gave 12
    # instead of ~72). TMP places the top of GlyphRect at baseline + bearingY;
    # for Latin accents without heavy descenders, bearingY ≈ inner height.
    bearing_x = float(bbox_lo[0]) if bbox_lo else 0.0
    bearing_y = float(inner_h)
    if char in "çÇÿ" and bbox_lo is not None:
        # Rough: keep a fraction of the ink below the baseline.
        _, descent = font_lo.getmetrics()
        bearing_y = float(max(inner_h - descent, inner_h * 0.7))

    return Glyph(
        char=char,
        unicode=ord(char),
        bitmap=crop,
        width=inner_w,
        height=inner_h,
        bearing_x=bearing_x,
        bearing_y=bearing_y,
        advance=advance,
    )


def pack_glyphs(
    glyphs: list[Glyph], atlas_size: int, padding: int
) -> tuple[np.ndarray, list[Glyph]]:
    """Skyline shelf packer. Returns Alpha8 atlas and glyphs with positions."""
    atlas = np.zeros((atlas_size, atlas_size), dtype=np.uint8)
    # Shelf packing: left to right, new row when full.
    x = y = row_h = 0
    placed: list[Glyph] = []
    for g in sorted(glyphs, key=lambda g: -g.bitmap.shape[0] * g.bitmap.shape[1]):
        bw, bh = g.bitmap.shape[1], g.bitmap.shape[0]
        if bw == 0 or bh == 0:
            # Space / empty: no atlas placement.
            placed.append(g)
            continue
        if x + bw > atlas_size:
            x = 0
            y += row_h
            row_h = 0
        if y + bh > atlas_size:
            raise SystemExit(
                f"Atlas {atlas_size}x{atlas_size} plein ({g.char!r} "
                f"{bw}x{bh} ne rentre pas a y={y})."
            )
        # See patch_font_atlas.pack_into_free: serialized atlas is bottom-up.
        atlas[y : y + bh, x : x + bw] = g.bitmap[::-1]
        g.atlas_x = x + padding  # GlyphRect origin = inner content
        g.atlas_y = y + padding
        placed.append(g)
        x += bw
        row_h = max(row_h, bh)
    return atlas, placed


def face_info(font_path: str, point_size: int) -> dict:
    """Approximate TMP FaceInfo from FreeType metrics."""
    font = ImageFont.truetype(font_path, point_size)
    ascent, descent = font.getmetrics()  # descent is positive downward in PIL
    # PIL getmetrics: ascent above baseline, descent below (positive).
    line_height = ascent + descent
    return {
        "m_PointSize": float(point_size),
        "m_Scale": 1.0,
        "m_LineHeight": float(line_height),
        "m_AscentLine": float(ascent),
        "m_CapLine": float(ascent * 0.97),  # refined per-font later if needed
        "m_MeanLine": float(ascent * 0.7),
        "m_Baseline": 0.0,
        "m_DescentLine": float(-descent),
        "m_SuperscriptOffset": float(ascent),
        "m_SubscriptOffset": float(-descent),
        "m_UnderlineOffset": float(-descent * 0.5),
        "m_UnderlineThickness": float(point_size * 0.05),
        "m_StrikethroughOffset": float(ascent * 0.3),
        "m_StrikethroughThickness": float(point_size * 0.05),
        "m_TabWidth": float(font.getlength(" ") * 4 if font.getlength(" ") else point_size * 0.3),
    }


def charset_french() -> list[str]:
    """ASCII printable + French accents the lots need."""
    basic = [chr(c) for c in range(32, 127)]
    accents = list(
        "àâäæçéèêëïîôœùûüÿÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ"
        "«»—–…’‘“”"
    )
    # Deduplicate, keep order.
    seen = set()
    out = []
    for ch in basic + accents:
        if ch not in seen:
            seen.add(ch)
            out.append(ch)
    return out


def build_atlas(
    font_path: str,
    point_size: int,
    chars: list[str],
    atlas_size: int = 1024,
    padding: int = 5,
    supersample: int = 8,
) -> tuple[np.ndarray, list[Glyph], dict]:
    glyphs = []
    for ch in chars:
        g = render_glyph(font_path, ch, point_size, padding, supersample)
        if g is not None:
            glyphs.append(g)
    atlas, placed = pack_glyphs(glyphs, atlas_size, padding)
    info = face_info(font_path, point_size)
    return atlas, placed, info
