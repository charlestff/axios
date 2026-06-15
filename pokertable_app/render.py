"""Render a table state (hole cards + board) to a pixel grid.

A pixel grid is a list of rows of ints (0 = background, 1 = ink). The same
layout constants are used by the OCR step to segment the image -- legitimate,
because we own the renderer. `add_noise` flips pixels to emulate a noisy
screen capture so the OCR study has something to measure.
"""
from __future__ import annotations

import random
from typing import List, Sequence, Tuple

from .glyphs import GH, GLYPHS, GW

CARD_GAP = 2          # blank columns between the two glyphs of one card
SLOT_GAP = 3          # blank columns between cards
MARGIN = 1
CARD_W = GW * 2 + CARD_GAP
ROW_H = GH + 2

Grid = List[List[int]]


def _blank(w: int, h: int) -> Grid:
    return [[0] * w for _ in range(h)]


def _stamp(grid: Grid, bitmap: List[List[int]], x0: int, y0: int) -> None:
    for y, row in enumerate(bitmap):
        for x, v in enumerate(row):
            if v:
                grid[y0 + y][x0 + x] = 1


def render_cards(cards: Sequence) -> Tuple[Grid, List[Tuple[int, int]]]:
    """Render a row of cards. Returns (grid, slot_origins) where slot_origins
    are the (x, y) pixel coordinates of each card for the OCR segmenter."""
    n = len(cards)
    w = MARGIN * 2 + n * CARD_W + (n - 1) * SLOT_GAP
    h = MARGIN * 2 + GH
    grid = _blank(max(w, 1), h)
    origins = []
    x = MARGIN
    for card in cards:
        label = repr(card)  # e.g. 'As', 'Td', '9h'
        origins.append((x, MARGIN))
        rank_ch, suit_ch = label[0], label[1]
        _stamp(grid, GLYPHS[rank_ch], x, MARGIN)
        _stamp(grid, GLYPHS[suit_ch], x + GW + CARD_GAP, MARGIN)
        x += CARD_W + SLOT_GAP
    return grid, origins


def add_noise(grid: Grid, p: float, rng: random.Random) -> Grid:
    """Flip each pixel with probability p (salt-and-pepper capture noise)."""
    if p <= 0:
        return [row[:] for row in grid]
    out = []
    for row in grid:
        out.append([(1 - v) if rng.random() < p else v for v in row])
    return out


def to_text(grid: Grid) -> str:
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
