"""OCR reliability study on our own table.

For each noise level: deal random Hold'em (2 cartas) or Draw (5 cartas) tables,
render them with our font, add capture noise, OCR them back, and measure how
often the recognised card label matches the ground truth the app already knows.

Run:  python -m pokertable_app.study
      python -m pokertable_app.study --game draw --deals 2000
"""
from __future__ import annotations

import argparse
import json
import random

from poker_sim.cards import Deck

from .ocr import recognize_grid
from .render import add_noise, render_cards


def deal_table(game: str, rng: random.Random):
    """Return the list of visible cards on the table for one hand."""
    deck = Deck(rng)
    if game == "holdem":
        hole = deck.deal(2)
        board = deck.deal(5)
        return hole + board
    return deck.deal(5)  # five card draw: the player's 5-card hand


def run(game: str, deals: int, noise_levels, seed: int):
    rng = random.Random(seed)
    rows = []
    for p in noise_levels:
        cards_total = 0
        cards_ok = 0
        chars_total = 0
        chars_ok = 0
        for _ in range(deals):
            cards = deal_table(game, rng)
            truth = [repr(c) for c in cards]
            grid, origins = render_cards(cards)
            noisy = add_noise(grid, p, rng)
            read = recognize_grid(noisy, origins)
            for t, r in zip(truth, read):
                cards_total += 1
                cards_ok += int(t == r)
                chars_total += 2
                chars_ok += int(t[0] == r[0]) + int(t[1] == r[1])
        rows.append({
            "noise": p,
            "card_accuracy": round(cards_ok / cards_total, 4),
            "char_accuracy": round(chars_ok / chars_total, 4),
        })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="OCR reliability study on our own table")
    ap.add_argument("--game", choices=["holdem", "draw"], default="holdem")
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    levels = [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
    rows = run(args.game, args.deals, levels, args.seed)
    print(f"OCR study -- game={args.game} deals={args.deals}")
    print(f"{'noise':>6} {'card_acc':>9} {'char_acc':>9}")
    for r in rows:
        print(f"{r['noise']:>6.2f} {r['card_accuracy']:>9.4f} {r['char_accuracy']:>9.4f}")
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
