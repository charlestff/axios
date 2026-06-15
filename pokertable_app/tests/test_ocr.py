"""OCR round-trip checks on our own renderer."""
import random

from poker_sim.cards import parse

from pokertable_app.ocr import recognize_grid
from pokertable_app.render import add_noise, render_cards
from pokertable_app.study import deal_table, run


def test_zero_noise_is_perfect():
    cards = [parse(c) for c in ["As", "Kd", "Qh", "Jc", "Ts", "9d", "2h"]]
    grid, origins = render_cards(cards)
    read = recognize_grid(grid, origins)
    assert read == [repr(c) for c in cards]


def test_all_glyphs_round_trip():
    # every rank and suit must read back exactly at zero noise
    ranks = "23456789TJQKA"
    suits = "cdhs"
    cards = [parse(r + s) for r in ranks for s in suits]
    grid, origins = render_cards(cards)
    assert recognize_grid(grid, origins) == [repr(c) for c in cards]


def test_accuracy_degrades_with_noise():
    rows = run("holdem", deals=200, noise_levels=[0.0, 0.2], seed=1)
    assert rows[0]["card_accuracy"] == 1.0
    assert rows[1]["card_accuracy"] < rows[0]["card_accuracy"]


def test_deal_table_sizes():
    rng = random.Random(0)
    assert len(deal_table("holdem", rng)) == 7
    assert len(deal_table("draw", rng)) == 5
