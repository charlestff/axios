"""Sanity checks for hand ranking and the table. Run: python -m pytest poker_sim"""
from poker_sim.cards import parse
from poker_sim.evaluator import best_of, category_name, rank_5


def h(*cs):
    return [parse(c) for c in cs]


def test_category_ordering():
    sf = rank_5(h("9s", "8s", "7s", "6s", "5s"))
    quads = rank_5(h("9s", "9d", "9c", "9h", "5s"))
    boat = rank_5(h("9s", "9d", "9c", "5h", "5s"))
    flush = rank_5(h("As", "Js", "9s", "5s", "2s"))
    straight = rank_5(h("9s", "8d", "7c", "6h", "5s"))
    trips = rank_5(h("9s", "9d", "9c", "Kh", "5s"))
    two_pair = rank_5(h("9s", "9d", "5c", "5h", "Ks"))
    pair = rank_5(h("9s", "9d", "Kc", "7h", "5s"))
    high = rank_5(h("As", "Jd", "9c", "7h", "5s"))
    order = [high, pair, two_pair, trips, straight, flush, boat, quads, sf]
    assert order == sorted(order)


def test_wheel_straight():
    assert category_name(rank_5(h("As", "2d", "3c", "4h", "5s"))) == "straight"
    # wheel is the lowest straight, below 2-6
    assert rank_5(h("As", "2d", "3c", "4h", "5s")) < rank_5(h("6s", "2d", "3c", "4h", "5s"))


def test_best_of_seven():
    # board flush beats a pair held in hand
    r = best_of(h("Ah", "Kd", "2s", "5s", "9s", "Js", "Qs"))
    assert category_name(r) == "flush"


def test_kicker_matters():
    a = rank_5(h("Ks", "Kd", "Ah", "7c", "5s"))
    b = rank_5(h("Ks", "Kd", "Qh", "7c", "5s"))
    assert a > b
