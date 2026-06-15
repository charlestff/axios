"""Cash-game invariants. The decisive check for side-pot logic is that every
hand is zero-sum: total chips won == total chips lost."""
import random

from poker_sim.agents import DisruptiveAgent, LooseHumanAgent, ProAgent
from poker_sim.cashgame import CashGame


def _agents(seed):
    r = random.Random(seed)
    return [
        DisruptiveAgent("D1", rng=random.Random(r.random() * 1e9), iters=10),
        DisruptiveAgent("D2", rng=random.Random(r.random() * 1e9), iters=10),
        ProAgent("Pro", rng=random.Random(r.random() * 1e9), iters=10),
        LooseHumanAgent("Loose", rng=random.Random(r.random() * 1e9), iters=10),
    ]


def test_each_hand_is_zero_sum_holdem():
    g = CashGame(_agents(1), game="holdem", rng=random.Random(1))
    for h in range(300):
        deltas, _ = g._play_hand(button=h % g.n)
        assert sum(deltas.values()) == 0, f"hand {h} not zero-sum: {deltas}"


def test_each_hand_is_zero_sum_draw():
    g = CashGame(_agents(2), game="draw", rng=random.Random(2))
    for h in range(300):
        deltas, _ = g._play_hand(button=h % g.n)
        assert sum(deltas.values()) == 0, f"hand {h} not zero-sum: {deltas}"


def test_session_runs_and_reports():
    g = CashGame(_agents(3), game="holdem", rng=random.Random(3))
    stats = g.play(200)
    s = stats.summary(g.agents, g.bb)
    assert s["_meta"]["hands"] == 200
    # net across all players is ~zero-sum (only differs by integer rounding of splits)
    total = sum(v["net_bb"] for k, v in s.items() if k != "_meta")
    assert abs(total) < 1.0
