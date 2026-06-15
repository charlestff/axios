"""Consolidated experiment report.

Run:  python -m poker_sim.experiments

Win-rate uses a moderate Monte Carlo budget (strategy quality matters there).
Detection uses a small budget on purpose: the timing signature the detector
reads is independent of how many equity samples the agent draws, so we trade
strategy precision for many more sessions.
"""
from __future__ import annotations

import json
import random
import time

from .agents import LooseHumanAgent, ProAgent, TightHumanAgent
from .simulation import jitter_sweep, run_detection, run_winrate


def winrate_agents(iters_pro=120):
    return [
        ProAgent("Pro", rng=random.Random(11), iters=iters_pro),
        TightHumanAgent("Tight", rng=random.Random(22), iters=60),
        LooseHumanAgent("Loose", rng=random.Random(33), iters=40),
    ]


def detect_agents(jitter=0.0):
    # low equity iters: strategy quality is irrelevant to the timing signature
    return [
        ProAgent("Pro", rng=random.Random(101), iters=20, jitter=jitter),
        TightHumanAgent("Tight", rng=random.Random(202), iters=20),
        LooseHumanAgent("Loose", rng=random.Random(303), iters=20),
    ]


def main():
    report = {}

    t0 = time.time()
    print("[1/5] Q1 win-rate -- Texas Hold'em (2 cartas)...", flush=True)
    report["winrate_holdem"] = run_winrate(winrate_agents(), hands=1000, game="holdem", seed=7)

    print("[2/5] Q1 win-rate -- Five Card Draw (5 cartas)...", flush=True)
    report["winrate_draw"] = run_winrate(winrate_agents(), hands=1000, game="draw", seed=7)

    print("[3/5] Q2 static detector (bot uses default regular timing)...", flush=True)
    report["detect_static"] = run_detection(detect_agents(0.0), hands=3000, batch=40, seed=1)

    print("[4/5] Q2 adaptive detector vs lightly-jittered bot...", flush=True)
    report["detect_adaptive"] = run_detection(
        detect_agents(0.3), hands=3000, batch=40, seed=1, adaptive=True)

    print("[5/5] Q2 jitter sweep (cat-and-mouse curve)...", flush=True)
    report["jitter_sweep"] = jitter_sweep(
        detect_agents, jitters=[0.0, 0.1, 0.2, 0.3, 0.5, 0.8],
        hands=2500, batch=40, seed=1)

    report["_runtime_sec"] = round(time.time() - t0, 1)
    with open("poker_sim_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n=== RESULTS ===")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
