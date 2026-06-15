"""A self-contained poker table.

Plays full hands of heads-up / multiway Texas Hold'em and Five Card Draw among
in-memory agents. Betting is no-limit style but bounded (a per-street raise cap
plus deep starting stacks) so hands always terminate and side-pots stay out of
scope -- which is plenty to measure whether a strategy wins.

Returns, for each hand, the chip delta per seat and the behavioural log the
detector consumes.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .agents import BaseAgent, Context
from .cards import Card, Deck
from .evaluator import best_of

RAISE_CAP = 4  # max aggressive actions per street -> guarantees termination


class HandResult:
    def __init__(self):
        self.deltas: Dict[int, int] = {}
        # behaviour log: list of (seat, decision_time, action_str)
        self.events: List[Tuple[int, float, str]] = []
        self.went_to_showdown = False


def _betting_round(H, order: List[int], current_bet: int) -> None:
    agents: List[BaseAgent] = H["agents"]
    cs = H["committed_street"]
    raises = 1 if current_bet > 0 else 0  # blind counts as the opening "bet"
    players_to_act = len([s for s in order if s in H["in_hand"]])
    ptr = 0
    n = len(order)

    while players_to_act > 0:
        if len(H["in_hand"]) <= 1:
            return
        seat = order[ptr % n]
        ptr += 1
        if seat not in H["in_hand"] or H["stacks"][seat] <= 0:
            players_to_act -= 1
            continue

        agent = agents[seat]
        to_call = current_bet - cs[seat]
        ctx = Context(
            hole=list(H["holes"][seat]),
            board=list(H["board"]),
            street=H["street"],
            to_call=to_call,
            pot=H["pot"],
            min_raise=max(H["bb"], current_bet - cs[seat] + H["bb"]),
            stack=H["stacks"][seat],
            n_active=len(H["in_hand"]),
            big_blind=H["bb"],
            game=H["game"],
            rng=H["rng"],
        )
        t = agent.decision_time()
        action, amount = agent.act(ctx)

        if action == "fold":
            H["in_hand"].discard(seat)
            H["events"].append((seat, t, "fold"))
            players_to_act -= 1
            continue

        if action in ("check", "call"):
            pay = min(to_call, H["stacks"][seat])
            _commit(H, seat, pay)
            H["events"].append((seat, t, "call" if to_call > 0 else "check"))
            players_to_act -= 1
            continue

        # raise
        if raises >= RAISE_CAP:
            # cap reached: downgrade to a call
            pay = min(to_call, H["stacks"][seat])
            _commit(H, seat, pay)
            H["events"].append((seat, t, "call"))
            players_to_act -= 1
            continue

        # pay to call, then raise on top
        raise_to = current_bet + max(H["bb"], amount)
        total_needed = raise_to - cs[seat]
        total_needed = min(total_needed, H["stacks"][seat])
        _commit(H, seat, total_needed)
        current_bet = cs[seat]
        raises += 1
        H["events"].append((seat, t, "raise"))
        # everyone still in must respond to the raise
        players_to_act = len([s for s in order if s in H["in_hand"] and H["stacks"][s] > 0]) - 1


def _commit(H, seat: int, amount: int) -> None:
    amount = max(0, amount)
    H["stacks"][seat] -= amount
    H["committed_street"][seat] += amount
    H["committed_total"][seat] += amount
    H["pot"] += amount


def play_hand(agents: List[BaseAgent], button: int, sb: int, bb: int,
              starting_stack: int, game: str, rng: random.Random) -> HandResult:
    n = len(agents)
    deck = Deck(rng)
    H = {
        "agents": agents,
        "stacks": {i: starting_stack for i in range(n)},
        "committed_total": {i: 0 for i in range(n)},
        "committed_street": {i: 0 for i in range(n)},
        "in_hand": set(range(n)),
        "pot": 0,
        "board": [],
        "holes": {},
        "bb": bb,
        "street": "preflop",
        "game": game,
        "rng": rng,
        "events": [],
    }

    # deal
    cards_each = 2 if game == "holdem" else 5
    for i in range(n):
        H["holes"][i] = deck.deal(cards_each)

    # blinds (heads-up: button is SB)
    if n == 2:
        sb_seat, bb_seat = button, (button + 1) % n
    else:
        sb_seat, bb_seat = (button + 1) % n, (button + 2) % n
    _commit(H, sb_seat, sb)
    _commit(H, bb_seat, bb)

    if game == "holdem":
        _play_holdem(H, button, bb_seat, bb, deck)
    else:
        _play_draw(H, button, bb_seat, bb, deck)

    # showdown / award
    res = HandResult()
    res.events = H["events"]
    _award(H, res)
    return res


def _order_from(seat: int, n: int) -> List[int]:
    return [(seat + k) % n for k in range(n)]


def _play_holdem(H, button, bb_seat, bb, deck) -> None:
    n = len(H["agents"])
    # preflop: action starts left of BB (heads-up: button/SB acts first)
    start = (bb_seat + 1) % n
    H["street"] = "preflop"
    _betting_round(H, _order_from(start, n), current_bet=bb)

    for street, deal_n in [("flop", 3), ("turn", 1), ("river", 1)]:
        if len(H["in_hand"]) <= 1:
            return
        H["board"].extend(deck.deal(deal_n))
        H["street"] = street
        for i in range(n):
            H["committed_street"][i] = 0
        post_start = (button + 1) % n
        _betting_round(H, _order_from(post_start, n), current_bet=0)


def _play_draw(H, button, bb_seat, bb, deck) -> None:
    n = len(H["agents"])
    start = (bb_seat + 1) % n
    H["street"] = "preflop"
    _betting_round(H, _order_from(start, n), current_bet=bb)

    # draw phase: pro/tight agents discard their weakest cards
    if len(H["in_hand"]) > 1:
        for seat in list(H["in_hand"]):
            keep = _draw_keep(H["holes"][seat])
            discards = 5 - len(keep)
            if discards:
                keep.extend(deck.deal(discards))
            H["holes"][seat] = keep

    if len(H["in_hand"]) <= 1:
        return
    H["street"] = "draw"
    for i in range(n):
        H["committed_street"][i] = 0
    _betting_round(H, _order_from((button + 1) % n, n), current_bet=0)


def _draw_keep(hand: List[Card]) -> List[Card]:
    """Keep pairs/trips/quads and high cards; discard the rest (simple policy)."""
    from collections import Counter
    counts = Counter(c.rank for c in hand)
    keep = [c for c in hand if counts[c.rank] >= 2]
    if not keep:  # no pair: keep highest 2 cards, draw 3
        keep = sorted(hand, key=lambda c: c.rank, reverse=True)[:2]
    return keep


def _award(H, res: HandResult) -> None:
    n = len(H["agents"])
    contenders = list(H["in_hand"])
    if len(contenders) == 1:
        winners = contenders
    else:
        res.went_to_showdown = True
        if H["game"] == "holdem":
            scores = {s: best_of(H["holes"][s] + H["board"]) for s in contenders}
        else:
            scores = {s: best_of(H["holes"][s]) for s in contenders}
        top = max(scores.values())
        winners = [s for s in contenders if scores[s] == top]

    share = H["pot"] // len(winners)
    rem = H["pot"] - share * len(winners)
    for i in range(n):
        res.deltas[i] = -H["committed_total"][i]
    for j, w in enumerate(winners):
        res.deltas[w] += share + (rem if j == 0 else 0)
