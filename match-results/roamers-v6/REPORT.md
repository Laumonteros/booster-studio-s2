# V6: sample field players + close support — rejected

Branch `devin/roamers-v6`, based on updated `origin/main` **fe7a90c** (PR #5).
**Nothing committed or pushed.** Source remains in the isolated local worktree
`/home/ubuntu/repos/booster-studio-s2-roamers-v6`. No v5 controller was carried over.

## Implementation and scope

- `team/src/field_player.py`: exact official sample Player, changing only imports
  to isolated field parameters/utilities. Its attack, plan_kick, walking, kick
  entry/exit, velocity and support algorithms are otherwise byte-identical.
- `field_params.py`: exact sample parameters except **SUPPORT_DIST_M 3.0→2.0**.
  The sample's goalward support line naturally drops toward the goal mouth in
  our half. This is the only field-player tuning addition.
- `field_utils/`: exact sample utilities, with namespaced parameter imports.
  This avoids leaking keeper parameters into field movement or vice versa.
- `field_logic.py`: sample closest-attacker selection/stickiness and phase
  actions, adapted to two field players: do not assign one of them as guard;
  normal play has one attacker/one supporter; kickoff locks its taker; opponent
  kickoff uses both waiting slots; READY skips the sample's guard slot.
- `roster.py`, `main.py`: preserve the original Player for robot 1 and construct
  sample Players for robots 2/3, with the same constructor/API and opt-in probes.
  Add private `store.fields` phase/role memory. Keep main's eligibility and
  unconditional stopped-phase safety gates. Keeper dispatch remains original.
- `tests/test_field_v6.py`, updated field expectations in `test_team_dispatch.py`:
  exact sample/import/parameter fidelity, original keeper construction,
  goalward 2 m support in both halves, missing-ball stop and phase dispatch.
- `scripts/check_support_telemetry.py`, `tests/test_support_reporting.py`:
  distinguish actual support spacing from commanded target distance, including
  a subset where the attacking roamer is within 1 m of the ball.

Keeper command body was AST-compared with main. Original `player.py`, `param.py`,
keeper helpers in `tactics.py`, keeper utilities, framework, telemetry module and
official sample are byte-identical to main. New factory/store state are additive;
Player constructor arguments and public methods remain compatible. Keeper
behavior can naturally see different teammate/ball positions, but no keeper
policy, constants or commands were changed.

## Two eight-match batches

Scores are **ours–sample**. Two concurrent games, alternating sides, four home
and four away in each batch. Every game reached natural `time_expired` after
600 regulation seconds; **zero failed launches**. Package/source were unchanged
between batches; the two complete source snapshots are byte-identical.

| Game | Side | Batch 01 score | Own fouls/falls/warnings | Batch 02 score | Own fouls/falls/warnings |
|---|---|---:|---|---:|---|
| 01 | Home | 2–3 | 0/0/1 | 3–3 | 0/0/0 |
| 02 | Away | 2–1 | 0/0/0 | 2–2 | 0/0/1 |
| 03 | Home | 3–4 | 0/0/0 | 1–1 | 1/0/1 |
| 04 | Away | 2–2 | 0/0/0 | 1–3 | 0/0/0 |
| 05 | Home | 2–1 | 2/1/2 | 1–3 | 1/0/0 |
| 06 | Away | 2–2 | 0/0/1 | 4–2 | 1/0/1 |
| 07 | Home | 1–2 | 1/0/1 | 3–3 | 0/0/0 |
| 08 | Away | 0–2 | 1/0/0 | 3–2 | 1/0/1 |

| Team/batch | W/D/L | GF–GA | Mean GD | Improvement vs −2.0 | Own fouls/falls/warnings |
|---|---|---|---:|---:|---|
| Main reference | 0/0/8 | 13–29 | −2.000 | — | — |
| V6 batch 01 | 2/2/4 | 14–17 | −0.375 | +1.625 | 4/1/5 |
| V6 batch 02 | 2/4/2 | 18–19 | −0.125 | +1.875 | 4/0/4 |
| **V6 pooled** | **4/6/6** | **32–36** | **−0.250** | **+1.750** | **8/1/9** |

The first scoring margin was only 0.125 beyond the required threshold, so a
second batch was run as requested despite already failing the safety gates.
Both batches meet the mean-GD/wins criteria. **The candidate does not qualify:**
one own fallen penalty and nine own set-play warnings violate the zero gates.
No third batch, further tuning, commit or push was attempted.

Own rule events across 16 games:
- Six `goal_disallowed_indirect` warnings. Do not add those to the valid score:
  making the restart legal changes the subsequent play, not just the scoreboard.
- Three opponent restart retakes: two `free_kick_avoidance_radius`, one
  `defender_set_play_interference` (goal kicks/throw-in).
- One fallen penalty: **batch 01, game 05, player 2**, sim 61.808 s. It was a
  roamer, not the unchanged keeper. Its physical cause was not established.
- Four `inactiveRobot` penalties and three restart-position/interference
  penalties, in addition to the fall, account for the eight own fouls.

## What telemetry shows

Logging was enabled via `--telemetry`/environment; the source flag stays off.
All 16 traces parsed without dropped records, malformed lines or writer errors.
Analysis is tick-weighted and restricted to normal PLAYING/non-stopped play,
with known ball/poses and an active support action, excluding restart waiting
and penalized/recovering players. Baseline is the earlier two fully instrumented
main games, measured with the same filter, not a new baseline benchmark.

| Spacing measure | Main telemetry | V6, 16 games |
|---|---:|---:|
| Normal support samples | 24,399 | 192,181 |
| Median commanded target→ball | 3.808 m | **2.000 m** |
| Median actual support→ball | 3.859 m | **2.963 m** |
| Median actual support→selected attacker | 3.288 m | **1.890 m** |
| Actual support→attacker in [1.5,2.5] m | 12.0% | **46.9%** |
| Median support→attacker, attacker within 1 m of ball | 3.465 m | **1.750 m** |
| That near-ball subset's samples | 8,667 | 71,741 |
| That subset within [1.5,2.5] m | 8.8% | **51.4%** |

**Support did move closer as intended**, especially around the near-ball attacker.
The selected attacker is a carrier proxy, not proof of possession; the near-ball
subset reduces that ambiguity but still does not establish physical control.
Commanded target distance lies within 1.5–2.5 m in **95.1%** of V6 samples; field/
goal-line clamping explains shorter targets. Actual support→ball is in that
range only **32.7%**, and its p90 is 6.133 m. The support is not always close:
chasing, role changes and fast ball movement still leave substantial lag.

### Observed inactivity risk of close support

All four inactive penalties were preceded by the supporter holding roughly
2 m from the ball, not by an attacking native task. The latest snapshots were
11–18 ms before the penalty, native kick inactive, with zero body velocity.
Across each preceding ~15 wall seconds, maximum displacement from the first
observed pose was only 0.017–0.068 m:

| Batch/game | Player | Ball distance before penalty | Maximum excursion |
|---|---:|---:|---:|
| 01/07 | 3 | 1.988 m | .030 m |
| 01/08 | 2 | 1.981 m | .017 m |
| 02/03 | 3 | 1.987 m | .068 m |
| 02/05 | 2 | 1.914 m | .037 m |

This checks the competing explanation that these were stuck attacking tasks:
all four observed actions were `support`, with no native kick active. The
reachable support→move_to_position→walk arrival/stop path holds its 2 m target
inside the documented 3 m inactivity radius. The referee confirms the inactivity
penalties; precise internal timer accumulation was not logged, and an ablation
against otherwise-identical 3 m support was not run. Do not attribute the overall
score gain, the single fall, or every rule failure solely to the support change.

The run supports the requested spacing change, but stock restart behavior and
stationary close support still need safety work. No such extra fixes were added
to this candidate.

## Checks and reproducibility

Policy/keeper/fidelity suite:
```
Ran 83 tests in 0.014s

OK
```
New support-reporting tests:
```
Ran 3 tests in 0.001s

OK
```
Build:
```
[0003.5s INFO] Agent package sign succeed
[0003.5s STEP] Build completed: laumonteros_team_v1-1.0.0.agent
```
Final retained-evidence validation:
```
PASS: 16 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 2 animations verified
```

Commands: `python3 scripts/check_team_results.py --results match-results/roamers-v6`
and `python3 scripts/check_support_telemetry.py match-results/roamers-v6`.
The basic repository rules were checked; no Booster 3v3 skill was available, so
this is not an official full rules audit. Actual referee logs expose the failures
above; no competition-readiness claim is made.

Artifacts under this directory:
- `batch-*/match-*/result.json`, `events.jsonl`, `summary.json`, `telemetry.jsonl.gz`.
- `batch-*/{source-snapshot,provenance,summary}.json`.
- `support-telemetry.json`, `baseline-support.json`, `inactivity-contexts.json`.
- `unit-tests.txt`, `reporting-tests.txt`, `validation.txt`, `build-output.txt`.
- Each batch's `match-01/evidence/match-timelapse.webp` and `snapshot-final.png`.

Batch 02's final snapshot was visually inspected: actual CPU-rendered finished
3–3 match, 0.0 s. Animations passed size/duration/provenance checks; these are
time-lapses, not real-time video. All files and raw traces are local-only and
mirrored to the primary repo's `match-results/roamers-v6/`. No packages, binaries,
certificates, keys, credentials or other files were committed or pushed.
