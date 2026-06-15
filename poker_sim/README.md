# Poker Strategy-vs-Detection Simulator

A **self-contained research simulator** for an Information Security study of
desktop-application automation and behavioural bot detection.

It answers two questions with reproducible experiments:

1. **Does a disciplined, equity-driven strategy actually win** at Texas Hold'em
   (2 hole cards) and Five Card Draw (5 cards)?
2. **Can a static behavioural detector** ("anti-cheat") tell an automated agent
   from human-like players from *timing alone* — and what happens when the bot
   is tuned (timing jitter) to look more human?

## Scope — read this first

This project is deliberately a **closed sandbox**:

- **No screen capture, no OCR, no template matching, no mouse/keyboard
  automation, no network.** It does not read from or send input to any
  application.
- It does **not** interact with PokerStars, GGPoker, PPoker or any real or
  third-party poker client, in play-money or real-money mode. The agents play
  only against *our own* in-memory table by calling Python functions.
- Because there is no input/output bridge, the agent code here is **not usable
  as a bot against a real client**. That bridge is intentionally absent and out
  of scope.

The "behaviour" the detector studies is a *synthetic decision-time number*
produced by the simulation, not observed from a real user. The goal is to study
detection methodology, not to defeat any real anti-cheat.

## Layout

| File | Role |
|------|------|
| `cards.py` | Card / deck primitives (pure in-memory) |
| `evaluator.py` | 5- and 7-card hand ranking (`rank_5`, `best_of`) |
| `equity.py` | Monte Carlo equity estimation |
| `agents.py` | Strategy + synthetic timing signature (`ProAgent`, human agents) |
| `table.py` | Hand engine: Hold'em + Five Card Draw, bounded no-limit betting |
| `detector.py` | Behavioural features + `StaticDetector` / `AdaptiveDetector` |
| `simulation.py` | Experiment harness (`run_winrate`, `run_detection`, `jitter_sweep`) |
| `experiments.py` | One-shot consolidated report -> `poker_sim_results.json` |
| `run_sim.py` | CLI |
| `tests/` | Hand-evaluator sanity checks |

## Running (Windows / macOS / Linux, Python 3.10+)

No third-party dependencies for the core (only `pytest` to run the tests).

```bash
# from the repository root
python -m poker_sim.run_sim winrate --game holdem --hands 1000
python -m poker_sim.run_sim winrate --game draw   --hands 1000
python -m poker_sim.run_sim detect  --hands 3000            # static detector
python -m poker_sim.run_sim detect  --hands 3000 --jitter 0.3 --adaptive
python -m poker_sim.run_sim sweep   --hands 2500            # cat-and-mouse curve

# cash game (persistent stacks, rebuys, side pots) -- both variants
python -m poker_sim.run_sim cash --game holdem --hands 3000             # 2 cartas
python -m poker_sim.run_sim cash --game draw   --hands 3000             # 5 cartas
python -m poker_sim.run_sim cash --game holdem --hands 3000 --disruptor # + maniac

# everything at once, writes poker_sim_results.json
python -m poker_sim.experiments

# tests
python -m pytest poker_sim -q
```

> On Windows use the same commands in PowerShell or `cmd` with `python`
> (or `py -3`). Install both "components" simply by copying this folder; there
> is nothing to install on the target machine beyond Python.

## How the detector works

Each seat emits a decision-time per action. The detector buckets a seat's times
into fixed-size **sessions** and computes:

- **coefficient of variation** (`std/mean`) — scripted actors are too consistent;
- **timing-histogram regularity** (1 − normalised entropy) — uniform timing is
  suspicious;
- fraction of very fast decisions, minimum time.

`StaticDetector` flags a session as a bot when CV is below a fixed threshold or
regularity is above one. `AdaptiveDetector` raises its CV threshold whenever it
*misses* a known bot — modelling "the anti-cheat is updated when it fails to
detect" — which is the lever for the cat-and-mouse experiment in
`jitter_sweep`.

## Interpreting results

- **Win-rate** is reported in `bb/100` (big blinds won per 100 hands), the
  standard poker yardstick. A consistently positive `bb/100` for the strategy
  agent across enough hands answers Q1.
- **Detection** reports accuracy, bot recall, and the human false-positive rate.
  The jitter sweep shows recall falling as the bot's timing is humanised — and
  the false-positive rate is the cost a stricter detector pays, which is the
  real-world tension for any anti-automation system.

This is the honest finding the study is after: a static behavioural detector
catches naive automation cheaply, but an adversary willing to randomise timing
erodes recall, and tightening the detector to compensate raises false positives
against legitimate users.
