"""OCR over our own rendered table.

Two backends:
  * `recognize_grid` -- a self-contained nearest-template matcher over our 5x7
    font. No external dependency; runs anywhere; used by the study.
  * `recognize_with_tesseract` -- optional, for the `--live` path on a real
    desktop where a screenshot of OUR app window is passed through pytesseract.

The segmenter uses the renderer's known geometry to crop each card. Because we
own both ends, recognition is exact at zero noise; the study measures decay
under added noise.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .glyphs import CHARSET, GH, GLYPHS, GW
from .render import CARD_GAP, Grid


def _crop(grid: Grid, x0: int, y0: int, w: int, h: int) -> List[List[int]]:
    out = []
    for y in range(y0, y0 + h):
        row = grid[y] if 0 <= y < len(grid) else []
        out.append([row[x] if 0 <= x < len(row) else 0 for x in range(x0, x0 + w)])
    return out


def _hamming(a: List[List[int]], b: List[List[int]]) -> int:
    d = 0
    for ra, rb in zip(a, b):
        for va, vb in zip(ra, rb):
            d += va ^ vb
    return d


def _match_glyph(cell: List[List[int]]) -> Tuple[str, int]:
    best_ch, best_d = "?", 10 ** 9
    for ch in CHARSET:
        d = _hamming(cell, GLYPHS[ch])
        if d < best_d:
            best_ch, best_d = ch, d
    return best_ch, best_d


def recognize_grid(grid: Grid, slot_origins: Sequence[Tuple[int, int]]) -> List[str]:
    """Read each card slot back into a 'Rs' string using the font templates."""
    labels = []
    for (x0, y0) in slot_origins:
        rank_cell = _crop(grid, x0, y0, GW, GH)
        suit_cell = _crop(grid, x0 + GW + CARD_GAP, y0, GW, GH)
        rank, _ = _match_glyph(rank_cell)
        suit, _ = _match_glyph(suit_cell)
        labels.append(rank + suit)
    return labels


def recognize_with_tesseract(image) -> Optional[str]:
    """Run pytesseract on a PIL image of OUR app window (live mode only).

    Returns recognised text, or None if pytesseract/tesseract is unavailable.
    """
    try:
        import pytesseract  # type: ignore
    except Exception:
        return None
    return pytesseract.image_to_string(image)
