"""A tiny 5x7 bitmap font for the characters a card label uses.

Ranks: 2 3 4 5 6 7 8 9 T J Q K A   Suits: c d h s

Because this is OUR app rendering with OUR font, the OCR step can recognise the
glyphs reliably -- the study then measures how that breaks down under pixel
noise, which is the interesting (and honest) part.
"""
from __future__ import annotations

from typing import Dict, List

GW, GH = 5, 7  # glyph width / height

_RAW: Dict[str, List[str]] = {
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#####", "    #", "   # ", "  ## ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "J": ["  ###", "   # ", "   # ", "   # ", "#  # ", "#  # ", " ##  "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "c": ["     ", "     ", " ####", "#    ", "#    ", "#    ", " ####"],
    "d": ["    #", "    #", " ####", "#   #", "#   #", "#   #", " ####"],
    "h": ["#    ", "#    ", "# ## ", "##  #", "#   #", "#   #", "#   #"],
    "s": ["     ", "     ", " ####", "#    ", " ### ", "    #", "#### "],
}


def glyph(ch: str) -> List[List[int]]:
    """Return the 7x5 bitmap (rows of 0/1) for a character."""
    rows = _RAW[ch]
    return [[1 if c == "#" else 0 for c in row] for row in rows]


GLYPHS: Dict[str, List[List[int]]] = {ch: glyph(ch) for ch in _RAW}
CHARSET = list(_RAW.keys())
