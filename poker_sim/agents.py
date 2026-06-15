"""Player agents.

Each agent exposes two things the rest of the system cares about:

  * act(ctx)         -> a betting decision for our simulated table
  * decision_time()  -> a *synthetic* think-time sample

The think-time is the behavioural signature the detector studies. Nothing here
observes or controls a real application; "behaviour" is just numbers our own
simulation produces. A strongly automated agent tends to emit very regular
timings, a human-like agent emits noisy, heavy-tailed timings.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .cards import Card
from .equity import draw_equity, holdem_equity

Action = Tuple[str, int]  # ('fold'|'check'|'call'|'raise', amount)


@dataclass
class Context:
    hole: List[Card]          # 2 cards (holdem) or current 5-card hand (draw)
    board: List[Card]
    street: str               # 'preflop','flop','turn','river' or 'draw'/'showdown'
    to_call: int
    pot: int
    min_raise: int
    stack: int
    n_active: int
    big_blind: int
    game: str                 # 'holdem' or 'draw'
    rng: random.Random


class BaseAgent:
    profile = "human"  # ground-truth label used only to score the detector

    def __init__(self, name: str, rng: Optional[random.Random] = None):
        self.name = name
        self.rng = rng or random.Random()

    # --- strategy -------------------------------------------------------
    def act(self, ctx: Context) -> Action:
        raise NotImplementedError

    def equity(self, ctx: Context, iters: int) -> float:
        opp = max(1, ctx.n_active - 1)
        if ctx.game == "holdem":
            return holdem_equity(ctx.hole, ctx.board, opp, iters=iters, rng=self.rng)
        return draw_equity(ctx.hole, opp, iters=iters, rng=self.rng)

    # --- behavioural signature -----------------------------------------
    def decision_time(self) -> float:
        """Seconds of 'thinking' before acting (synthetic)."""
        return abs(self.rng.gauss(1.5, 0.6)) + 0.2


def _pot_odds(ctx: Context) -> float:
    if ctx.to_call <= 0:
        return 0.0
    return ctx.to_call / (ctx.pot + ctx.to_call)


class ProAgent(BaseAgent):
    """Equity-driven strategy meant to approximate strong, disciplined play.

    `jitter` emulates the idea of an automated agent being *tuned* to look more
    human over time -- it only changes the timing signature, never the strategy.
    This is the knob the detector-robustness experiment turns.
    """

    profile = "bot"

    def __init__(self, name="Pro", rng=None, iters=300, aggression=1.0, jitter=0.0):
        super().__init__(name, rng)
        self.iters = iters
        self.aggression = aggression
        self.jitter = jitter

    def act(self, ctx: Context) -> Action:
        eq = self.equity(ctx, self.iters)
        odds = _pot_odds(ctx)

        # value / continuation thresholds, loosely calibrated by opponent count
        raise_thr = 0.62 + 0.02 * (ctx.n_active - 2)
        call_margin = 0.04

        if ctx.to_call == 0:
            if eq >= raise_thr:
                size = max(ctx.min_raise, int(self.aggression * 0.7 * ctx.pot))
                return ("raise", min(size, ctx.stack))
            # occasional small bluff with weak equity to stay balanced
            if eq < 0.30 and self.rng.random() < 0.12:
                return ("raise", min(ctx.min_raise, ctx.stack))
            return ("check", 0)

        if eq >= raise_thr and ctx.stack > ctx.to_call + ctx.min_raise:
            size = max(ctx.min_raise, int(self.aggression * 0.7 * ctx.pot))
            return ("raise", min(size, ctx.stack))
        if eq >= odds + call_margin:
            return ("call", min(ctx.to_call, ctx.stack))
        return ("fold", 0)

    def decision_time(self) -> float:
        # very regular timing -- the tell of an unmodified bot
        base = abs(self.rng.gauss(0.85, 0.05)) + 0.05
        if self.jitter > 0:
            # "improvement": add human-like noise / occasional long pauses
            base += abs(self.rng.gauss(0, self.jitter))
            if self.rng.random() < 0.05 * (self.jitter / 0.5):
                base += self.rng.uniform(1.0, 4.0)
        return base


class TightHumanAgent(BaseAgent):
    profile = "human"

    def __init__(self, name="Tight", rng=None, iters=120):
        super().__init__(name, rng)
        self.iters = iters

    def act(self, ctx: Context) -> Action:
        eq = self.equity(ctx, self.iters)
        odds = _pot_odds(ctx)
        if ctx.to_call == 0:
            if eq >= 0.70:
                return ("raise", min(ctx.min_raise, ctx.stack))
            return ("check", 0)
        if eq >= 0.75 and ctx.stack > ctx.to_call + ctx.min_raise:
            return ("raise", min(ctx.min_raise, ctx.stack))
        if eq >= odds + 0.08:
            return ("call", min(ctx.to_call, ctx.stack))
        return ("fold", 0)

    def decision_time(self) -> float:
        # lognormal-ish, heavy tail, with sporadic long tank
        t = math.exp(self.rng.gauss(0.2, 0.5))
        if self.rng.random() < 0.10:
            t += self.rng.uniform(1.0, 6.0)
        return t + 0.2


class LooseHumanAgent(BaseAgent):
    profile = "human"

    def __init__(self, name="Loose", rng=None, iters=80):
        super().__init__(name, rng)
        self.iters = iters

    def act(self, ctx: Context) -> Action:
        eq = self.equity(ctx, self.iters)
        if ctx.to_call == 0:
            if eq >= 0.55 and self.rng.random() < 0.6:
                return ("raise", min(ctx.min_raise, ctx.stack))
            return ("check", 0)
        # calls too often regardless of odds
        if eq >= 0.30 or self.rng.random() < 0.35:
            return ("call", min(ctx.to_call, ctx.stack))
        return ("fold", 0)

    def decision_time(self) -> float:
        t = math.exp(self.rng.gauss(0.0, 0.6))
        if self.rng.random() < 0.12:
            t += self.rng.uniform(0.8, 5.0)
        return t + 0.15
