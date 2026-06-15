"""Behavioural detector -- the defensive / research side.

It never sees an agent's strategy or internals. It only receives the stream of
*decision times* a seat produced over a batch of hands (a "session") and decides
bot vs human from statistical regularity. Real anti-automation systems lean on
the same intuition: scripted actors are too consistent.

Two variants are provided:
  * StaticDetector   -- fixed thresholds (the "static anti-cheat").
  * AdaptiveDetector -- nudges its threshold when it MISSES a known bot, to
                        study the cat-and-mouse against an agent that adds jitter.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple


def extract_features(times: Sequence[float]) -> Dict[str, float]:
    n = len(times)
    if n < 2:
        return {"n": n, "mean": 0.0, "std": 0.0, "cv": 1.0,
                "fast_frac": 0.0, "min": 0.0, "regularity": 0.0}
    mean = sum(times) / n
    var = sum((t - mean) ** 2 for t in times) / (n - 1)
    std = math.sqrt(var)
    cv = std / mean if mean > 0 else 1.0          # coefficient of variation
    fast_frac = sum(1 for t in times if t < 0.6) / n
    # regularity: 1 - normalized entropy of a coarse timing histogram.
    # high regularity == suspiciously uniform timing.
    buckets = [0] * 10
    lo, hi = min(times), max(times)
    span = (hi - lo) or 1.0
    for t in times:
        b = min(9, int((t - lo) / span * 10))
        buckets[b] += 1
    probs = [c / n for c in buckets if c]
    ent = -sum(p * math.log(p) for p in probs)
    max_ent = math.log(10)
    regularity = 1.0 - (ent / max_ent if max_ent else 0.0)
    return {"n": n, "mean": mean, "std": std, "cv": cv,
            "fast_frac": fast_frac, "min": min(times), "regularity": regularity}


@dataclass
class StaticDetector:
    """Flags a session as a bot when timing is too regular.

    Decision rule (fixed): bot if coefficient of variation is below cv_threshold
    OR the timing histogram is highly concentrated (regularity high).
    """
    cv_threshold: float = 0.35
    regularity_threshold: float = 0.45

    def score(self, times: Sequence[float]) -> float:
        f = extract_features(times)
        # higher => more bot-like
        s = 0.0
        s += max(0.0, (self.cv_threshold - f["cv"]) / self.cv_threshold)
        s += max(0.0, (f["regularity"] - self.regularity_threshold))
        return s

    def predict(self, times: Sequence[float]) -> Tuple[str, float]:
        f = extract_features(times)
        is_bot = f["cv"] < self.cv_threshold or f["regularity"] > self.regularity_threshold
        return ("bot" if is_bot else "human", self.score(times))


@dataclass
class AdaptiveDetector(StaticDetector):
    """Static-by-default, but loosens/tightens its CV threshold when it misses a
    known bot. Models 'anti-cheat updated as it fails to detect'."""
    step: float = 0.02
    max_cv: float = 0.8
    history: List[float] = field(default_factory=list)

    def update_on_miss(self, true_label: str, predicted: str) -> None:
        self.history.append(self.cv_threshold)
        if true_label == "bot" and predicted == "human":
            # raise the bar so the next equally-regular bot is caught
            self.cv_threshold = min(self.max_cv, self.cv_threshold + self.step)


@dataclass
class DetectionReport:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    def add(self, true_label: str, predicted: str) -> None:
        if true_label == "bot" and predicted == "bot":
            self.tp += 1
        elif true_label == "human" and predicted == "bot":
            self.fp += 1
        elif true_label == "human" and predicted == "human":
            self.tn += 1
        else:
            self.fn += 1

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    @property
    def recall(self) -> float:  # of real bots, how many caught
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def false_positive_rate(self) -> float:  # humans wrongly flagged
        d = self.fp + self.tn
        return self.fp / d if d else 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "sessions": self.total, "tp": self.tp, "fp": self.fp,
            "tn": self.tn, "fn": self.fn, "accuracy": round(self.accuracy, 3),
            "bot_recall": round(self.recall, 3), "precision": round(self.precision, 3),
            "human_false_positive_rate": round(self.false_positive_rate, 3),
        }
