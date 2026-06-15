"""Poker hand evaluation.

`rank_5` returns a comparable tuple where larger == stronger, so two hands can
be compared directly with normal tuple comparison. Categories:

    8 straight flush, 7 four of a kind, 6 full house, 5 flush, 4 straight,
    3 trips, 2 two pair, 1 pair, 0 high card
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import List, Sequence, Tuple

from .cards import Card

HandRank = Tuple[int, ...]


def rank_5(cards: Sequence[Card]) -> HandRank:
    values = sorted((c.rank for c in cards), reverse=True)
    is_flush = len({c.suit for c in cards}) == 1

    distinct = sorted(set(values), reverse=True)
    straight_high = None
    if len(distinct) == 5:
        if distinct[0] - distinct[4] == 4:
            straight_high = distinct[0]
        elif distinct == [14, 5, 4, 3, 2]:  # wheel A-2-3-4-5
            straight_high = 5

    counts = Counter(values)
    # order by (count desc, value desc): e.g. full house -> trips first, pair second
    ordered = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    pattern = [c for _, c in ordered]
    by_count = [v for v, _ in ordered]

    if is_flush and straight_high:
        return (8, straight_high)
    if pattern == [4, 1]:
        return (7, by_count[0], by_count[1])
    if pattern == [3, 2]:
        return (6, by_count[0], by_count[1])
    if is_flush:
        return (5, *values)
    if straight_high:
        return (4, straight_high)
    if pattern == [3, 1, 1]:
        return (3, by_count[0], *by_count[1:])
    if pattern == [2, 2, 1]:
        return (2, by_count[0], by_count[1], by_count[2])
    if pattern == [2, 1, 1, 1]:
        return (1, by_count[0], *by_count[1:])
    return (0, *values)


def best_of(cards: Sequence[Card]) -> HandRank:
    """Best 5-card rank out of 5, 6 or 7 cards."""
    if len(cards) == 5:
        return rank_5(cards)
    return max(rank_5(combo) for combo in combinations(cards, 5))


CATEGORY_NAMES = {
    8: "straight flush", 7: "four of a kind", 6: "full house", 5: "flush",
    4: "straight", 3: "three of a kind", 2: "two pair", 1: "pair", 0: "high card",
}


def category_name(rank: HandRank) -> str:
    return CATEGORY_NAMES[rank[0]]
