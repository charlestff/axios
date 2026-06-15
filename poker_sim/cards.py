"""Card primitives for the self-contained poker research simulator.

This module has no I/O, no screen capture, no OCR and no input automation.
Cards are plain in-memory objects used only by our own simulated table.
"""
from __future__ import annotations

import random
from typing import List

RANKS = "23456789TJQKA"
SUITS = "cdhs"  # clubs, diamonds, hearts, spades
RANK_VALUE = {r: i for i, r in enumerate(RANKS, start=2)}  # '2'->2 ... 'A'->14
VALUE_RANK = {v: r for r, v in RANK_VALUE.items()}


class Card:
    __slots__ = ("rank", "suit")

    def __init__(self, rank: int, suit: int):
        # rank: 2..14, suit: 0..3
        self.rank = rank
        self.suit = suit

    def __eq__(self, other) -> bool:
        return isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return self.rank * 4 + self.suit

    def __repr__(self) -> str:
        return f"{VALUE_RANK[self.rank]}{SUITS[self.suit]}"


def make_deck() -> List[Card]:
    return [Card(r, s) for r in range(2, 15) for s in range(4)]


FULL_DECK = make_deck()


class Deck:
    """A shuffled 52-card deck we deal from. Pure in-memory state."""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.cards = make_deck()
        self.rng.shuffle(self.cards)

    def deal(self, n: int) -> List[Card]:
        out = self.cards[:n]
        del self.cards[:n]
        return out


def parse(s: str) -> Card:
    """Parse 'As', 'Td', '2c' -> Card. Convenience for tests."""
    return Card(RANK_VALUE[s[0].upper()], SUITS.index(s[1].lower()))
