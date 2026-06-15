"""Monte Carlo equity estimation against random opponents.

Used by the strategy agents to evaluate a holding. This is ordinary poker
math applied to our own simulated cards -- there is no connection to any
external client.
"""
from __future__ import annotations

import random
from typing import List, Sequence

from .cards import Card, make_deck
from .evaluator import best_of


def holdem_equity(
    hole: Sequence[Card],
    board: Sequence[Card],
    n_opponents: int,
    iters: int = 400,
    rng: random.Random | None = None,
) -> float:
    """Win-probability estimate for Texas Hold'em (2 hole cards).

    Ties are counted as a fractional win (split pot).
    """
    rng = rng or random.Random()
    known = set(hole) | set(board)
    deck = [c for c in make_deck() if c not in known]

    need_board = 5 - len(board)
    score = 0.0
    for _ in range(iters):
        draw = rng.sample(deck, 2 * n_opponents + need_board)
        i = 0
        opp_hands = []
        for _o in range(n_opponents):
            opp_hands.append(draw[i:i + 2])
            i += 2
        full_board = list(board) + draw[i:i + need_board]

        my = best_of(list(hole) + full_board)
        best_opp = max(best_of(oh + full_board) for oh in opp_hands)
        if my > best_opp:
            score += 1.0
        elif my == best_opp:
            score += 0.5
    return score / iters


def draw_equity(
    hand: Sequence[Card],
    n_opponents: int,
    iters: int = 400,
    rng: random.Random | None = None,
) -> float:
    """Win-probability for a fixed 5-card hand vs random 5-card hands."""
    rng = rng or random.Random()
    known = set(hand)
    deck = [c for c in make_deck() if c not in known]
    my = best_of(list(hand))
    score = 0.0
    for _ in range(iters):
        draw = rng.sample(deck, 5 * n_opponents)
        best_opp = max(
            best_of(draw[o * 5:o * 5 + 5]) for o in range(n_opponents)
        )
        if my > best_opp:
            score += 1.0
        elif my == best_opp:
            score += 0.5
    return score / iters
