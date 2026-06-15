"""Our own desktop poker table + an OCR study that runs on top of it.

The target of the OCR study is THIS application's own rendered table -- a
surface we fully control and know the ground truth of. It does not capture,
read, or target PokerStars / GGPoker / PPoker or any third-party client.
The point is to study the screen-capture -> OCR -> verify pipeline (and how
reliable it is under noise) against a controlled target.
"""
