"""Experiment harness.

Two questions:
  Q1  Does the equity-driven 'pro' strategy actually win? -> run_winrate
  Q2  Can a static detector tell the bot from humans, and what happens when the
      bot adds timing jitter to look human? -> run_detection / jitter_sweep
"""
from __future__ import annotations

import random
from typing import Dict, List, Sequence

from .agents import BaseAgent
from .detector import AdaptiveDetector, DetectionReport, StaticDetector
from .table import play_hand


def run_winrate(agents: Sequence[BaseAgent], hands: int, game: str = "holdem",
                sb: int = 1, bb: int = 2, starting_stack: int = 400,
                seed: int = 0) -> Dict[str, Dict[str, float]]:
    rng = random.Random(seed)
    n = len(agents)
    totals = {i: 0 for i in range(n)}
    showdowns = 0
    for h in range(hands):
        button = h % n
        res = play_hand(list(agents), button, sb, bb, starting_stack, game, rng)
        for i, d in res.deltas.items():
            totals[i] += d
        showdowns += int(res.went_to_showdown)

    out = {}
    for i, ag in enumerate(agents):
        chips = totals[i]
        bb_won = chips / bb
        out[ag.name] = {
            "profile": ag.profile,
            "chips": chips,
            "bb_won": round(bb_won, 1),
            "bb_per_100": round(bb_won / hands * 100, 2),
        }
    out["_meta"] = {"hands": hands, "game": game, "showdown_rate": round(showdowns / hands, 3)}
    return out


def _collect_sessions(agents: Sequence[BaseAgent], hands: int, game: str,
                      batch: int, seed: int) -> List[Dict]:
    """Play hands and bucket each seat's decision times into fixed-size sessions."""
    rng = random.Random(seed)
    n = len(agents)
    buffers: Dict[int, List[float]] = {i: [] for i in range(n)}
    sessions: List[Dict] = []
    for h in range(hands):
        button = h % n
        res = play_hand(list(agents), button, 1, 2, 400, game, rng)
        for seat, t, _action in res.events:
            buffers[seat].append(t)
            if len(buffers[seat]) >= batch:
                sessions.append({"seat": seat, "profile": agents[seat].profile,
                                 "times": buffers[seat]})
                buffers[seat] = []
    return sessions


def run_detection(agents: Sequence[BaseAgent], hands: int = 2000, game: str = "holdem",
                  batch: int = 40, seed: int = 1, detector: StaticDetector | None = None,
                  adaptive: bool = False) -> Dict:
    detector = detector or (AdaptiveDetector() if adaptive else StaticDetector())
    sessions = _collect_sessions(agents, hands, game, batch, seed)
    report = DetectionReport()
    for s in sessions:
        label, _score = detector.predict(s["times"])
        report.add(s["profile"], label)
        if adaptive and isinstance(detector, AdaptiveDetector):
            detector.update_on_miss(s["profile"], label)
    result = report.as_dict()
    if adaptive and isinstance(detector, AdaptiveDetector):
        result["final_cv_threshold"] = round(detector.cv_threshold, 3)
    return result


def jitter_sweep(make_agents, jitters: Sequence[float], hands: int = 2000,
                 game: str = "holdem", batch: int = 40, seed: int = 1) -> List[Dict]:
    """For each jitter level, rebuild agents (bot tuned with that jitter) and
    measure how detection degrades -- the cat-and-mouse curve."""
    rows = []
    for j in jitters:
        agents = make_agents(j)
        rep = run_detection(agents, hands=hands, game=game, batch=batch, seed=seed)
        rows.append({"jitter": j, **{k: rep[k] for k in
                     ("bot_recall", "human_false_positive_rate", "accuracy")}})
    return rows
