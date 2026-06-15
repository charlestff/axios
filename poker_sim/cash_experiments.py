"""Cash-game experiments with a disruptive (maniac) agent.

Table: Disruptor (bot) + Pro (bot) + Tight (human) + Loose (human), persistent
100bb stacks, rebuy on bust. Runs Texas Hold'em (2 cards) and Five Card Draw
(5 cards). Reports win-rate, variance, max drawdown and rebuys, plus whether the
behavioural detector still catches the (regular-timing) bots.

Run:  python -m poker_sim.cash_experiments
"""
from __future__ import annotations

import json
import random
import time

from .agents import DisruptiveAgent, LooseHumanAgent, ProAgent, TightHumanAgent
from .cashgame import CashGame
from .detector import DetectionReport, StaticDetector


def make_table(seed):
    r = random.Random(seed)
    return [
        DisruptiveAgent("Disruptor", rng=random.Random(r.random() * 1e9), iters=25, shove_freq=0.6),
        ProAgent("Pro", rng=random.Random(r.random() * 1e9), iters=25),
        TightHumanAgent("Tight", rng=random.Random(r.random() * 1e9), iters=25),
        LooseHumanAgent("Loose", rng=random.Random(r.random() * 1e9), iters=25),
    ]


def run_variant(game, hands, seed):
    agents = make_table(seed)
    game_obj = CashGame(agents, buyin_bb=100, game=game, rng=random.Random(seed))
    behavior = []
    stats = game_obj.play(hands, behavior_log=behavior)
    result = stats.summary(agents, game_obj.bb)

    # detection: bucket each seat's decision times into sessions of 40
    buffers = {i: [] for i in range(len(agents))}
    report = DetectionReport()
    det = StaticDetector()
    for seat, t, _action in behavior:
        buffers[seat].append(t)
        if len(buffers[seat]) >= 40:
            label, _ = det.predict(buffers[seat])
            report.add(agents[seat].profile, label)
            buffers[seat] = []
    result["_detection"] = report.as_dict()
    return result


def main():
    out = {}
    t0 = time.time()
    print("[1/2] Cash game -- Texas Hold'em (2 cartas) with Disruptor...", flush=True)
    out["cash_holdem"] = run_variant("holdem", hands=3000, seed=7)
    print("[2/2] Cash game -- Five Card Draw (5 cartas) with Disruptor...", flush=True)
    out["cash_draw"] = run_variant("draw", hands=3000, seed=7)
    out["_runtime_sec"] = round(time.time() - t0, 1)

    with open("poker_cash_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n=== CASH GAME RESULTS ===")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
