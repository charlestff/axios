"""Cash-game (ring-game) engine with persistent stacks and correct side pots.

Differences from `table.py` (which resets stacks every hand):

  * stacks carry over hand to hand;
  * players who bust are reloaded to the buy-in (rebuy) so the game continues,
    and rebuys are counted for risk metrics but do not distort net winnings;
  * all-ins are first-class and pots are split into side pots by the standard
    layered algorithm -- needed once a disruptive maniac starts shoving.

Still a closed sandbox: no I/O of any kind, only our own in-memory cards.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from .agents import BaseAgent, Context
from .cards import Card, Deck
from .evaluator import best_of

RAISE_CAP = 6  # cap on full raises among non-all-in players (all-ins are exempt)


@dataclass
class CashStats:
    deltas: Dict[int, List[float]] = field(default_factory=dict)  # per-hand bb deltas
    rebuys: Dict[int, int] = field(default_factory=dict)
    hands: int = 0

    def summary(self, agents: Sequence[BaseAgent], bb: int) -> Dict:
        out = {}
        for i, ag in enumerate(agents):
            d = self.deltas.get(i, [])
            net_chips = sum(d)
            net_bb = net_chips / bb
            mean = net_bb / len(d) if d else 0.0
            var = (sum((x / bb - mean) ** 2 for x in d) / len(d)) if d else 0.0
            # max drawdown of the cumulative bb curve
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for x in d:
                cum += x / bb
                peak = max(peak, cum)
                max_dd = max(max_dd, peak - cum)
            out[ag.name] = {
                "profile": ag.profile,
                "net_bb": round(net_bb, 1),
                "bb_per_100": round(net_bb / self.hands * 100, 2) if self.hands else 0.0,
                "std_bb_per_hand": round(var ** 0.5, 2),
                "max_drawdown_bb": round(max_dd, 1),
                "rebuys": self.rebuys.get(i, 0),
            }
        out["_meta"] = {"hands": self.hands, "big_blind": bb}
        return out


class CashGame:
    def __init__(self, agents: List[BaseAgent], buyin_bb: int = 100,
                 sb: int = 1, bb: int = 2, game: str = "holdem",
                 rng: random.Random | None = None):
        self.agents = agents
        self.n = len(agents)
        self.bb = bb
        self.sb = sb
        self.buyin = buyin_bb * bb
        self.game = game
        self.rng = rng or random.Random()
        self.stacks = {i: self.buyin for i in range(self.n)}
        self.stats = CashStats(deltas={i: [] for i in range(self.n)},
                               rebuys={i: 0 for i in range(self.n)})

    # --- session --------------------------------------------------------
    def play(self, hands: int, behavior_log: List | None = None) -> CashStats:
        for h in range(hands):
            for i in range(self.n):  # rebuy busted players to the buy-in
                if self.stacks[i] < self.bb:
                    self.stacks[i] = self.buyin
                    self.stats.rebuys[i] += 1
            deltas, events = self._play_hand(button=h % self.n)
            for i in range(self.n):
                self.stats.deltas[i].append(deltas[i])
                self.stacks[i] += deltas[i]
            if behavior_log is not None:
                behavior_log.extend(events)
            self.stats.hands += 1
        return self.stats

    # --- one hand -------------------------------------------------------
    def _play_hand(self, button: int):
        n = self.n
        deck = Deck(self.rng)
        H = {
            "holes": {}, "board": [], "in_hand": set(range(n)),
            "committed_total": {i: 0 for i in range(n)},
            "committed_street": {i: 0 for i in range(n)},
            "stacks": dict(self.stacks),  # work on a copy; commit deltas at end
            "start_stacks": dict(self.stacks),
            "pot": 0, "events": [], "street": "preflop",
        }
        cards_each = 2 if self.game == "holdem" else 5
        for i in range(n):
            H["holes"][i] = deck.deal(cards_each)

        if n == 2:
            sb_seat, bb_seat = button, (button + 1) % n
        else:
            sb_seat, bb_seat = (button + 1) % n, (button + 2) % n
        self._commit(H, sb_seat, min(self.sb, H["stacks"][sb_seat]))
        self._commit(H, bb_seat, min(self.bb, H["stacks"][bb_seat]))

        if self.game == "holdem":
            self._run_holdem(H, button, bb_seat, deck)
        else:
            self._run_draw(H, button, bb_seat, deck)

        deltas = self._settle(H)
        return deltas, H["events"]

    def _commit(self, H, seat, amount):
        amount = max(0, min(amount, H["stacks"][seat]))
        H["stacks"][seat] -= amount
        H["committed_street"][seat] += amount
        H["committed_total"][seat] += amount
        H["pot"] += amount

    # --- streets --------------------------------------------------------
    def _run_holdem(self, H, button, bb_seat, deck):
        n = self.n
        self._betting(H, self._order((bb_seat + 1) % n), current_bet=self.bb)
        for street, k in [("flop", 3), ("turn", 1), ("river", 1)]:
            if len(H["in_hand"]) <= 1:
                return
            H["board"].extend(deck.deal(k))
            H["street"] = street
            for i in range(n):
                H["committed_street"][i] = 0
            self._betting(H, self._order((button + 1) % n), current_bet=0)

    def _run_draw(self, H, button, bb_seat, deck):
        n = self.n
        self._betting(H, self._order((bb_seat + 1) % n), current_bet=self.bb)
        if len(H["in_hand"]) > 1:
            for seat in list(H["in_hand"]):
                keep = self._draw_keep(H["holes"][seat])
                need = 5 - len(keep)
                if need:
                    keep.extend(deck.deal(need))
                H["holes"][seat] = keep
        if len(H["in_hand"]) <= 1:
            return
        H["street"] = "draw"
        for i in range(n):
            H["committed_street"][i] = 0
        self._betting(H, self._order((button + 1) % n), current_bet=0)

    @staticmethod
    def _draw_keep(hand):
        from collections import Counter
        counts = Counter(c.rank for c in hand)
        keep = [c for c in hand if counts[c.rank] >= 2]
        if not keep:
            keep = sorted(hand, key=lambda c: c.rank, reverse=True)[:2]
        return keep

    def _order(self, start):
        return [(start + k) % self.n for k in range(self.n)]

    # --- betting (all-in aware) ----------------------------------------
    def _betting(self, H, order, current_bet):
        cs = H["committed_street"]
        raises = 1 if current_bet > 0 else 0
        to_act = len([s for s in order if s in H["in_hand"] and H["stacks"][s] > 0])
        ptr = 0
        L = len(order)

        while to_act > 0:
            if len(H["in_hand"]) <= 1:
                return
            seat = order[ptr % L]
            ptr += 1
            if seat not in H["in_hand"] or H["stacks"][seat] <= 0:
                to_act -= 1
                continue

            agent = self.agents[seat]
            to_call = current_bet - cs[seat]
            ctx = Context(
                hole=list(H["holes"][seat]), board=list(H["board"]),
                street=H["street"], to_call=to_call, pot=H["pot"],
                min_raise=max(self.bb, current_bet - cs[seat] + self.bb),
                stack=H["stacks"][seat], n_active=len(H["in_hand"]),
                big_blind=self.bb, game=self.game, rng=self.rng,
            )
            t = agent.decision_time()
            action, amount = agent.act(ctx)

            if action == "fold":
                H["in_hand"].discard(seat)
                H["events"].append((seat, t, "fold"))
                to_act -= 1
                continue

            if action in ("check", "call"):
                self._commit(H, seat, min(to_call, H["stacks"][seat]))
                H["events"].append((seat, t, "call" if to_call > 0 else "check"))
                to_act -= 1
                continue

            # raise
            going_all_in = amount >= H["stacks"][seat] - to_call
            if raises >= RAISE_CAP and not going_all_in:
                self._commit(H, seat, min(to_call, H["stacks"][seat]))
                H["events"].append((seat, t, "call"))
                to_act -= 1
                continue

            raise_to = current_bet + max(self.bb, amount)
            need = min(raise_to - cs[seat], H["stacks"][seat])
            self._commit(H, seat, need)
            H["events"].append((seat, t, "raise"))
            if cs[seat] > current_bet:  # a genuine raise reopens action
                current_bet = cs[seat]
                raises += 1
                to_act = len([s for s in order
                              if s in H["in_hand"] and H["stacks"][s] > 0]) - 1
            else:  # all-in for less than a full raise: treat as a call
                to_act -= 1

    # --- settlement with side pots -------------------------------------
    def _settle(self, H) -> Dict[int, float]:
        n = self.n
        contribs = dict(H["committed_total"])
        in_hand = H["in_hand"]
        deltas = {i: -H["committed_total"][i] for i in range(n)}

        if len(in_hand) <= 1:
            score = {s: (0,) for s in in_hand}  # uncontested: no comparison needed
        elif self.game == "holdem":
            score = {s: best_of(H["holes"][s] + H["board"]) for s in in_hand}
        else:
            score = {s: best_of(H["holes"][s]) for s in in_hand}

        dead = 0
        while any(v > 0 for v in contribs.values()):
            m = min(v for v in contribs.values() if v > 0)
            layer_contributors = [s for s in range(n) if contribs[s] > 0]
            pot = m * len(layer_contributors)
            for s in layer_contributors:
                contribs[s] -= m
            eligible = [s for s in layer_contributors if s in in_hand]
            if not eligible:
                dead += pot
                continue
            pot += dead
            dead = 0
            top = max(score[s] for s in eligible)
            winners = [s for s in eligible if score[s] == top]
            share = pot // len(winners)
            rem = pot - share * len(winners)
            for j, w in enumerate(winners):
                deltas[w] += share + (rem if j == 0 else 0)

        if dead > 0 and in_hand:  # folded over-contribution -> best remaining hand
            top = max(score[s] for s in in_hand)
            for w in [s for s in in_hand if score[s] == top]:
                deltas[w] += dead // len([s for s in in_hand if score[s] == top])
        return deltas
