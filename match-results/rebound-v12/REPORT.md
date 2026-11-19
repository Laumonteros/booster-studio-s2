# V12 close rebound support — reject for promotion

Branch `devin/rebound-v12`, from merged main `6c2c637`. No PR.

**V12 is substantially worse than V11: 2W/1D/13L, 21–50, mean GD −1.8125.**
The GD delta is **−2.3125/game**. Do not merge this candidate. No tuning or
strategy changes were made between its batches, despite the poor first batch.

## Every completed match

Scores are **ours–official sample**; F/W is our fallen penalties/warning events.
All sixteen counted matches ended naturally after 600 regulation simulation
seconds. Each batch has four home/four away slots, alternating by match number.

| Match | Side | Batch 01 score | F/W | Batch 02 score | F/W |
|---|---|---:|---:|---:|---:|
| 01 | Home | 1–3 | 0/0 | 1–2 | 0/0 |
| 02 | Away | 1–3 | 0/1 | 0–5 | 0/0 |
| 03 | Home | 2–3 | 0/0 | 1–4* | 0/0 |
| 04 | Away | 0–4 | 0/1 | 1–3 | 0/0 |
| 05 | Home | 0–5 | 0/0 | 2–3 | 0/0 |
| 06 | Away | 1–3 | 0/0 | 2–2 | 0/0 |
| 07 | Home | 0–4 | 0/0 | 4–0 | 0/0 |
| 08 | Away | 3–1 | 1/0 | 2–5 | 0/0 |

*Batch 02 match 03 originally failed **before kickoff**: opponent activation
never completed; the opponent supervisor recorded `uds connection closed`.
It was retried after the other slots with identical package/image/source and
the same home assignment. Original failure retained at
`batch-02/match-03-attempt-01/failure.json`; retry provenance is alongside the
batch provenance. There were 17 launches, 16 regulation games. No started game
was cancelled or selected out. The exact activation failure cause is unverified.

| Version | Games | W/D/L | GF–GA | Mean GD | GF/game | GA/game | Falls | Own warnings |
|---|---:|---|---|---:|---:|---:|---:|---:|
| V11 reference | 16 | 8/3/5 | 37–29 | +0.5000 | 2.3125 | 1.8125 | 1 | 3 |
| V12 batch 01 | 8 | 1/0/7 | 8–26 | −2.2500 | 1.0000 | 3.2500 | 1 | 2 |
| V12 batch 02 | 8 | 1/1/6 | 13–24 | −1.3750 | 1.6250 | 3.0000 | 0 | 0 |
| **V12 combined** | **16** | **2/1/13** | **21–50** | **−1.8125** | **1.3125** | **3.1250** | **1** | **2** |

| Own warning type / reason | V11 | V12 |
|---|---:|---:|
| Avoidance-radius retake | 1 | 0 |
| Defender-interference retake | 1 | 1 |
| Kickoff goal disallowed | 0 | 1 |
| Indirect goal disallowed | 0 | 0 |
| Stuck-ball reset advisory | 1 | 0 |
| **Total** | **3** | **2** |

Warnings are attributed to the offender, not always the awarded kicking side.
One additional V12 global no-touch/stuck-game warning had no actor and is not
assigned to either team. Falls mean referee fallen penalties, not every topple.
V12 had **zero inactivity penalties**, versus V11's two. Its other penalties:
one defender interference and one SET field-boundary violation.

## What the rebound evidence actually said

Full pre-benchmark measurement and counterevidence: `REBOUND_FINDINGS.md` and
`baseline-rebound-audit.json` (both V9 and V11, 32 games).

We measured 385 resolved short loose-flight windows, including 14 potential
opponent-deflection rebounds: opponent next proximity 314, original support 47,
other own robot 24. Median support distance to the subsequent recovery point
was **3.557 m**, versus **0.612 m** for the nearest opponent. An idealized flank
station reduces that support distance to 1.979 m, but would flip only **two**
opponent-won endpoint distance races with a 0.3 m margin.

Equal-speed flight-interception sensitivity models gave **9–14** potentially
flippable lost races, but also **gave up existing pickups**: at the middle speed,
actual support led in 51 windows versus 21 at the hypothetical fixed flank.
Thus the telemetry did **not** establish a net-gain cause or a large stock of
guaranteed recoverable rebounds. This was a controlled positioning experiment,
not a physically validated recovery predictor. Shots, contact and possession
cannot be established by native requests or proximity alone; long/unobserved
flights and ambiguous races are excluded rather than counted as losses.

## What the same frozen V12 implementation did

Changed strategy files only:
- `team/src/rebound_support.py`: normal-play close flanking station, side
  hysteresis, selected-shot-ray/attacker clearance, clipping fallbacks, a short
  no-yaw local patrol, and pose-progress inactivity escape.
- `team/src/rebound_params.py`: isolated constants.
- `team/src/field_logic.py`: only the normal support hook.

It trails in our half and blends toward a goalward flank in the attacking half.
Keeper, attacker selection, native attacking/shooting primitives, throw-in
handoff, opponent exit, kickoff/restart handlers and framework are unchanged.
No V10 cap was carried over. Strategy uses only Context and its own player
memory; no added disk/network I/O, sleeps or private simulator access.

| Measured runtime behavior | V11: 16 | V12: 16 |
|---|---:|---:|
| Median normal-play support-labeled roamer distance from ball | 2.849 m | **3.172 m** |
| Resolved short loose flights | 193 | 155 |
| Original support next proximity | 19/193 (9.8%) | 15/155 (9.7%) |
| Any own robot next proximity | 34/193 (17.6%) | 39/155 (25.2%) |
| Median support→ball at flight start | 2.532 m | 2.209 m |
| Median support→recovery point | 3.537 m | 3.282 m |
| Goal-zone request flight windows | 44 | 18 |
| Normal-play attacker identity switches | 304 | 289 |
| Longest continuous near-ball support span without 0.25 m pose progress | 15.11 wall s | 7.98 wall s |

The controller engaged: **174,130** `support:rebound` samples, **6,222**
`support:escape` samples, **89** observed escape entries. There were another
2,196 plain `support`-labeled normal-play samples, not counted as new-controller
engagement. Labels alone do not prove current actionability or accepted motion.
**381,584 ticks**, no drops/writer errors.

Eight native stop errors were recorded (V11 reference: two), all during recovery
or stopped release, in batch 01 matches 07/08 and batch 02 match 04:
`RuntimeError('API call failed, code = 400')`. All games completed; these are
retained in the runtime audit, not diagnosed as the cause of the regression.

**The sustained-close-support objective was not achieved**: the whole-normal-
play distance increased even though loose-flight-start distances improved.
Support's own proximity recovery rate was essentially unchanged. Team recovery
rate improved in this conditional cohort, but scoring and conceding regressed
severely. These different cohorts/volumes are not causal proof. Attacker churn
did not increase, which argues against that simple explanation of the regression.
The precise physical mechanism of the scoring collapse remains unverified.

## Remaining incident contexts

- Batch 01 match 02: own kickoff goal disallowed at **626.648 sim s**.
- Batch 01 match 04: player 3 defender interference on an opponent goal kick,
  **522.450 sim s**. Latest observed action was stopped with accepted zero
  velocity. This does not prove absence of residual contact.
- Batch 01 match 08: player 3 fallen penalty, **67.354 sim s**. Last non-recovery
  action was the unchanged `restart:short_pass` 11.59 wall seconds earlier,
  power 1.5; at the penalty it was recovering. Physical trigger unverified.
- Batch 02 match 04: player 3 SET boundary penalty, **228.640 sim s**. Latest
  action was unchanged READY at team-frame x≈−7.718 m, y≈5.097 m, with turn-only
  request. Earlier normal positioning could affect initial conditions; unchanged
  handlers alone do not exonerate interactions with the new positioning.

`runtime-support-audit.json` retains per-match engagement/progress counts and
penalty snapshots. Nonzero commands are not treated as proof of physical motion.
Zero inactivity penalties is the observed result, not a universal guarantee.

## Checks and provenance

```
Ran 130 tests in 0.575s

OK
```

```
PASS: 16 complete regulation results/event timelines, 1 recorded failed launches; source provenance and summary counts match; 2 animations verified
```

All **38 source/config snapshot entries**, package SHA256, simulator image and
official sample revision match across both batches, the retry and current source.
Package SHA256: `3653cb06e7be3abf86f85ab85a8527e9670c293d9baf4bf4ddd12e44fb61dcec`.
Build log reports `Signer-sign success` and `Agent package sign succeed`.

Tests cover mirrored/edge geometry, lane clearance, attacker spacing, side
hysteresis, short-step motion, physical-progress stalls, resets on observation
gaps, missing observations, all protected phases, real Player native release,
normal dispatch, empty/bad telemetry, rebound windows and archived launch failures.

Booster 3v3 skill remains unavailable in this environment. Checks are repository
tests, basic rules/scope checks and actual referee evidence, not a full skill-based
rules audit; an upgraded development environment is needed for that audit.

## Evidence

Final CPU-rendered 1–3 snapshot visually inspected. This is rendering evidence,
not a still-image proof of rebound behavior; engagement is measured above.

Time-lapses (local-only binaries, mirrored under the primary repo):
```
/home/ubuntu/repos/booster-studio-s2/match-results/rebound-v12/batch-01/match-01/evidence/match-timelapse.webp
/home/ubuntu/repos/booster-studio-s2/match-results/rebound-v12/batch-02/match-01/evidence/match-timelapse.webp
```
`snapshot-final.png` is alongside each. Raw compressed telemetry, animations,
packages and signing material are not committed. Structured results, timelines,
source/provenance, audits and logs are committed. No PR opened.
