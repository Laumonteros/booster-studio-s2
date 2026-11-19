# V11: one normal-play scoring fix

Branch `devin/scoring-v11` from `origin/main` at
**ff2de4b7afd02b5a754333164131d4048956b634**. No V10 speed cap carried over.
Only strategy change: select an available goal-mouth lane for the normal
attacker instead of always aiming through the center. Keeper, throw-in handoff,
opponent exit, all restart dispatch, support, walking, power and kick thresholds
are unchanged. No PR or merge.

## V9 rerun completed first

The unchanged second V9 batch was validated and pushed on `devin/v9-rerun` at
**92c3cf2a1a0316acc946661c3dbddad8d5039518** before V11 was implemented.
Its source-hash mapping exactly matches V9 batch 01.

| V9 batch | Games | W/D/L | GF–GA | Mean GD | Falls | Own warning events |
|---|---:|---|---|---:|---:|---:|
| 01 | 8 | 4/2/2 | 21–16 | +0.6250 | 2 | 1 |
| 02 | 8 | 4/1/3 | 16–12 | +0.5000 | 1 | 1 |
| **Combined baseline** | **16** | **8/3/5** | **37–28** | **+0.5625** | **3** | **2** |

V9 batch 02 ours–sample scores, alternating home/away:
**1–0, 3–2, 2–1, 1–2, 1–2, 2–3, 4–0, 2–2**.
The one fall was game 02; the one indirect-goal warning was game 04.
The combined baseline has one avoidance-radius retake and one disallowed
indirect goal. Full rerun table and validation are on that branch in
`match-results/set-plays-v9/RERUN.md` and `v9-16-game-aggregate.json`.

## Final chance-loss finding

See `CHANCES.md` for definitions, reachability checks, counterexamples and the
complete method; `v9-chance-audit.json` retains per-match/episode measurements.
Preliminary exploratory counts are superseded by the following numbers, which
credit immediate deflected goals and use the actual behind-goal baseline aim.

| Normal-play in-range last-touch outcome | V9 batch 01 | V9 batch 02 | Total |
|---|---:|---:|---:|
| Scored, including immediate opponent deflection | 19 | 16 | **35** |
| Non-scoring, every close request's center lane obstructed | 30 | 50 | **80** |
| Non-scoring, no close in-range request | 29 | 27 | **56** |
| Non-scoring, at least one clear center request | 14 | 15 | **29** |
| **Total** | **92** | **108** | **200** |

The biggest measured non-scoring category was **center-only obstructed requests**.
**54/80** such episodes had a clear off-center alternative. There were 626 total
last-touch episodes; range is at most 4.5 m from goal, close requests at most
0.8 m from the attacking roamer. These proxies do not assert physical possession,
actual shot attempts or physical blocks. Two match goals lie outside this cohort.

Actual command directions were checked independently: **9,137/9,137** close,
in-range normal updates across the full V9 traces aimed toward **(7.25,0)**,
matching the default `plan_kick` source path (maximum error 8.88e−16 radians).
Thus the policy really ignored alternative lanes in this scenario; it was not
merely a code path that could theoretically execute.

Counterevidence: **12** episodes scored despite all their close center requests
being geometrically obstructed. The model is not a save detector; goalkeeper
motion, ball height and native foot behavior remain unobserved. This is a
measured policy omission and an experiment, not proof that it caused 80 misses.

Other hypotheses were kept separate:
- 56 non-scoring in-range episodes had no close request, smaller than 80.
- 494/626 episodes included close-ball requests outside shooting range, but
  native tasks also dribble/clear; these cannot be called 494 wasted shots.
- Support was over 2.5 m away at 48/115 fresh opponent-recovery observations.
  This overlaps other categories and does not prove 48 missed rebounds/passes.
  Neither support, approach thresholds nor long-range kicking were changed.

## Implementation and tests

- `team/src/field_shooting.py`: pure public-Context geometry and one remembered
  goal-mouth ordinate per field player. Only normal `attack` in ball-free
  PLAYING, inside the 4.5 m goal zone, is eligible. Missing state/pose/ball,
  keeper ID 1, stopped/other phases, restart ownership/clocks and all handoff/
  exit actions bypass it.
- Three candidates: the **original (7.25,0)** center target and physical
  goal-mouth targets **(7,−1), (7,+1)**, 0.3 m inside the posts. Clearance uses
  their goal-plane segments. A clear current lane is retained; switching between
  obstructed lanes requires a 0.15 m improvement. Comfortable center clearance
  restores center aim. When center is selected, its direction is exactly V9's.
- `field_shooting_params.py`: four isolated constants. No shared parameter edits.
- `field_player.py`: one import, one target expression in `plan_kick`, and its
  docstring. Native task start/stop/ownership, power, chase/support geometry,
  approach thresholds and backend methods remain byte-identical to V9.
- `tests/test_field_shooting.py`: blocked/clear/unknown lanes, original aim-depth
  fidelity, hysteresis, real Player/native-request integration, every protected
  set play, missing observations, pauses, keeper exclusion and shooting range.
- Existing sample-source fidelity test allows exactly the import/target/docstring
  changes and still compares all remaining sample Player/utility/parameter code.
- `scripts/analyze_scoring.py` and `tests/test_scoring_analysis.py`: offline-only
  reproducible diagnostics, including deflected-goal credit, empty/no-request
  cases, restart exclusion and rejection of malformed telemetry. Never imported
  by submitted strategy logic.

## Final V11 benchmark

All **eight final matches** ended naturally after **600 regulation seconds**,
alternating four home/four away, telemetry on, two concurrent workers. Identical
corrected source/package throughout; zero failed launches. Final batch is
**batch-02**. Two incomplete pilot matches were cancelled before any completed
regulation result when the aim-depth cross-check caught an unnecessary clear-
center change. Their source/logs are preserved separately; they are not part of
this benchmark. See `pilot-exclusion.json` and `CHANCES.md`.

Scores are ours–sample. Counts are our team's referee events.

| Game | Side | Score | Result | Penalties | Falls | Warning events |
|---|---|---:|---|---:|---:|---:|
| 01 | Home | 1–1 | Draw | 0 | 0 | 0 |
| 02 | Away | 4–0 | Win | 0 | 0 | 0 |
| 03 | Home | 4–1 | Win | 0 | 0 | 0 |
| 04 | Away | 3–2 | Win | 0 | 0 | 1 |
| 05 | Home | 1–0 | Win | 0 | 0 | 0 |
| 06 | Away | 2–1 | Win | 0 | 0 | 0 |
| 07 | Home | 3–4 | Loss | 0 | 0 | 0 |
| 08 | Away | 2–0 | Win | 0 | 0 | 0 |

| Candidate | Games | W/D/L | GF–GA | Mean GD | Falls | Own warnings |
|---|---:|---|---|---:|---:|---:|
| V9 combined | 16 | 8/3/5 | 37–28 | +0.5625 | 3 | 2 |
| **V11** | **8** | **6/1/1** | **20–9** | **+1.3750** | **0** | **1** |

Mean GD improves **0.8125/game**. Wins: 75% versus 50%. GF/game: **2.5000 vs
2.3125**; GA/game: **1.1250 vs 1.7500**. Most of the GD difference is fewer
concessions, not a large scoring-rate jump. This is a promising single eight-
game result, **not statistically established consistency or causal attribution
of the entire result to aiming**. Falls mean fallen penalties, not every recovery.

### Warnings by type

| Type / reason | V9: 16 games | V11: 8 games |
|---|---:|---:|
| `set_play_retake:free_kick_avoidance_radius` | 1 | **0** |
| `goal_disallowed_indirect:indirect_goal_requirement_not_satisfied` | 1 | **0** |
| `ball_reset:clear_stuck_ball` | 0 | **1** |
| All other own warning types | 0 | 0 |

V11's single warning is game 04, simTime **195.482 s**, attributed to the unchanged
**keeper/player 1**. The auto-referee nudged a stuck ball after 712 ms of contact
and only 2.8 mm movement. It is a stuck-ball reset, not an avoidance/indirect-goal
violation or a penalty. Full event: `remaining-warning.json`. No keeper fix made.

## Did the intended command behavior change?

181,945 telemetry ticks parsed with no drops/writer errors or native errors.
There were **10,340 off-center** and **4,504 original-center** normal in-range
native updates. All **49,983** normal updates outside the shooting zone retained
the exact original behind-goal aim.

Of **5,309** close in-range normal requests, the selected lane was obstructed in
**2,259 (42.55%)**, compared with **3,976 (74.89%)** for the original center ray
on those **same V11 snapshots**. **1,717** requests moved from an obstructed
center ray to a clear selected lane. These are command samples, not independent
shots, saves prevented or goals added. Remaining all-lane crowding is not solved.

## Checks and evidence

```
Ran 115 tests in 0.298s

OK
```
```
PASS: 8 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 1 animations verified
```
V9 rerun validation:
```
PASS: 16 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 2 animations verified
```
Scope audit:
```
PASS: keeper, throw-in handoff, opponent exit, dispatch, support, movement, kick power/thresholds, shared parameters, framework and official opponent unchanged from ff2de4b
```

Exact outputs: `unit-tests.txt`, `validation.txt`, `scope-audit.txt`,
`build-output.txt`. Commands:
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/check_team_results.py --results match-results/scoring-v11
```

Time-lapses:
- V9 rerun: `match-results/set-plays-v9/batch-02/match-01/evidence/match-timelapse.webp`
- V11 final: `match-results/scoring-v11/batch-02/match-01/evidence/match-timelapse.webp`

Both final CPU-rendered snapshots were visually inspected (V9 1–0; V11 1–1);
their paths are `snapshot-final.png` beside each animation. All result artifacts
are mirrored beneath `/home/ubuntu/repos/booster-studio-s2/match-results/`.
Only text/code/results are committed. Raw gzip telemetry, images/animations,
packages and signing material stay local-only. The Booster 3v3 skill is absent;
checks use repository/basic rules and actual referee evidence, not a full skill-
based rules audit. Pushed as requested; no PR.
