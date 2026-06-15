"""CLI entry point. Runs the two experiments and prints a report.

Examples (Windows / macOS / Linux, Python 3.10+):

    python -m poker_sim.run_sim winrate --game holdem --hands 5000
    python -m poker_sim.run_sim winrate --game draw   --hands 5000
    python -m poker_sim.run_sim detect  --hands 3000
    python -m poker_sim.run_sim sweep   --hands 3000
"""
from __future__ import annotations

import argparse
import json
import random

from .agents import LooseHumanAgent, ProAgent, TightHumanAgent
from .simulation import jitter_sweep, run_detection, run_winrate


def _table(rng_seed: int, jitter: float = 0.0):
    r = random.Random(rng_seed)
    return [
        ProAgent("Pro", rng=random.Random(r.random() * 1e9), iters=250, jitter=jitter),
        TightHumanAgent("Tight", rng=random.Random(r.random() * 1e9)),
        LooseHumanAgent("Loose", rng=random.Random(r.random() * 1e9)),
    ]


def cmd_winrate(args):
    agents = _table(args.seed)
    out = run_winrate(agents, hands=args.hands, game=args.game, seed=args.seed)
    print(json.dumps(out, indent=2))


def cmd_detect(args):
    agents = _table(args.seed, jitter=args.jitter)
    out = run_detection(agents, hands=args.hands, game=args.game,
                        batch=args.batch, seed=args.seed, adaptive=args.adaptive)
    print(json.dumps(out, indent=2))


def cmd_sweep(args):
    rows = jitter_sweep(lambda j: _table(args.seed, jitter=j),
                        jitters=[0.0, 0.1, 0.2, 0.3, 0.5, 0.8],
                        hands=args.hands, game=args.game, batch=args.batch, seed=args.seed)
    print(f"{'jitter':>7} {'bot_recall':>11} {'fpr':>7} {'accuracy':>9}")
    for r in rows:
        print(f"{r['jitter']:>7.2f} {r['bot_recall']:>11.3f} "
              f"{r['human_false_positive_rate']:>7.3f} {r['accuracy']:>9.3f}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Poker strategy-vs-detection simulator")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--game", choices=["holdem", "draw"], default="holdem")
    common.add_argument("--hands", type=int, default=3000)
    common.add_argument("--seed", type=int, default=0)
    common.add_argument("--batch", type=int, default=40)

    w = sub.add_parser("winrate", parents=[common]); w.set_defaults(func=cmd_winrate)

    d = sub.add_parser("detect", parents=[common])
    d.add_argument("--jitter", type=float, default=0.0)
    d.add_argument("--adaptive", action="store_true")
    d.set_defaults(func=cmd_detect)

    s = sub.add_parser("sweep", parents=[common]); s.set_defaults(func=cmd_sweep)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
