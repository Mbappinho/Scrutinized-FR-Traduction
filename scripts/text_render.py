# -*- coding: utf-8 -*-
"""
Bridge between the French stored in the lots and the French written to the game.

The lots hold **properly accented** French: it is the translation, and losing it
would mean retranslating everything once the fonts can render it. But the TMP
atlases shipped with the game carry no French glyph, so an accented character
falls through to LiberationSans and renders in a visibly different typeface.

So the text is folded to ASCII on its way into the asset files. Every script that
needs to know what the player will actually see goes through `rendered()`.

Flipping `ACCENTS_AVAILABLE` to True after the font phase is the only change
needed to bring the accents back — no retranslation.
"""
from __future__ import annotations

import unicodedata

# Set to True once the atlases carry the Latin-1 glyphs. See PATCH_MENUS_FR.md,
# section « Accents ».
ACCENTS_AVAILABLE = True

# Characters that NFD cannot decompose, plus punctuation absent from the atlases.
# The typographic apostrophe is missing from every atlas of the game, including
# in English, where it already falls back to another typeface.
SUBSTITUTIONS = {
    "œ": "oe",
    "Œ": "OE",
    "æ": "ae",
    "Æ": "AE",
    "ß": "ss",
    "’": "'",
    "‘": "'",
    "‛": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "«": '"',
    "»": '"',
    "–": "-",
    "—": "-",
    "―": "-",
    "…": "...",
    "\u00a0": " ",  # espace insecable
    "\u202f": " ",  # espace fine insecable
    "\u2009": " ",
    "\u2011": "-",
    "•": "-",
    "€": "EUR",
}


def fold_to_ascii(text: str) -> str:
    """Strip diacritics and replace punctuation the atlases cannot draw.

    Decomposing first and dropping the combining marks covers every accented
    letter in one go, uppercase included, instead of a table that will always be
    missing a case.
    """
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.combining(ch):
            continue
        out.append(SUBSTITUTIONS.get(ch, ch))
    return "".join(out)


def rendered(text: str) -> str:
    """What the player will see, given the current state of the atlases."""
    return text if ACCENTS_AVAILABLE else fold_to_ascii(text)


# Glyphs we bake into every expanded atlas. Anything outside this set (and
# outside ASCII) still needs a SUBSTITUTIONS entry or it will draw as blank.
ATLAS_LATIN1 = set(
    "àâäæçéèêëïîôœùûüÿÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ«»"
    "…—"  # ellipsis already in most atlases; em-dash we may fold
)


def unrenderable(text: str) -> list[str]:
    """Characters the current atlases cannot draw."""
    shown = rendered(text)
    if not ACCENTS_AVAILABLE:
        return sorted({ch for ch in shown if not ch.isascii()})
    # Accents on: allow ASCII + the Latin-1 set we injected. Unknown symbols
    # (smart quotes we forgot to fold, etc.) still fail loudly.
    return sorted(
        {
            ch
            for ch in shown
            if not ch.isascii() and ch not in ATLAS_LATIN1
        }
    )
