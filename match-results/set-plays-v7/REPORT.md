# V7 set-play safeguards: failed benchmark, record only

V6 was committed/pushed as `2d28bdacc8071042aeae3381b467895d7e9ec646` on
`devin/roamers-v6`, then merged by the lead as PR #6. That supersedes the original
v6 report's historical no-push decision. V7 was cut fresh from merged main
`4c58f084487b25028804b1c46428e6805b58b0bd`, on **devin/set-plays-v7**.
No PR was opened and no merge performed by this session.

## Decision

**Do not promote V7.** Revised gate: no worse than V6's −0.25 mean GD, fewer
set-play warnings and fewer falls. Compare incident rates because V6 has 16 games
and this batch has eight. V7 improves warnings but regresses GD and falls.
This is neither thin nor a single-incident failure; no second batch was run.
The branch is pushed for the record as requested, including the failed attempt.

| Team | Games | W/D/L | GF–GA | Mean GD | Own fouls | Own fallen penalties | Own set-play warnings |
|---|---:|---|---|---:|---:|---:|---:|
| V6 reference | 16 | 4/6/6 | 32–36 | −0.250 | 8 | 1 | 9 |
| V7 | 8 | 2/0/6 | 17–29 | **−1.500** | 12 | **4** | **1** |

GF/game increased 2.000→2.125, but GA/game worsened 2.250→3.625. This bundled
experiment does not isolate how much the handoff, escape behavior or penalties
contributed to those changes. The goal of a safe, non-regressing candidate was
not achieved.

Scores are **ours–sample**. All games finished naturally with `time_expired`
after **600 regulation seconds**, four home/four away, two concurrently.

| Game | Side | Score | Outcome | Our fouls | Our falls | Our set-play warnings |
|---|---|---:|---|---:|---:|---:|
| 01 | Home | 4–3 | Win | 1 | 0 | 0 |
| 02 | Away | 2–3 | Loss | 0 | 0 | 0 |
| 03 | Home | 3–4 | Loss | 1 | 1 | 0 |
| 04 | Away | 1–6 | Loss | 6 | 1 | 0 |
| 05 | Home | 2–5 | Loss | 1 | 0 | 0 |
| 06 | Away | 1–5 | Loss | 3 | 2 | 0 |
| 07 | Home | 2–0 | Win | 0 | 0 | 1 |
| 08 | Away | 2–3 | Loss | 0 | 0 | 0 |

## V6 evidence checked before implementation

`v6-incident-audit.json` preserves all six disallowed-goal event chains and all
three retake contexts. **All six disallowed attacking goals followed throw-ins**,
not goal kicks or kickoffs: placement → one recorded own robot touch → ball-free
→ `goal_disallowed_indirect/indirect_goal_requirement_not_satisfied`, without a
recorded second-robot touch. The warning is authoritative; the number of physical
kicks cannot be inferred just by counting persistent native sessions/events.

NOTES.md requires two different robot touches OR a decisive touch >0.5 m from
the restart point. Official ball-free alone does not waive this requirement.
To be conservative this attempt applied a short-pass handoff to all our restarts,
including kickoffs; that broader choice introduced a new kickoff-position bug.

Two V6 retakes were goal-kick avoidance-radius failures. Just before the retake,
the offending roamers were 1.166/1.245 m away, already beyond the endline at
x≈7.07/7.14 in team coordinates, issuing retreat commands. The third was a
throw-in defender touch: the latest public snapshot still said **stopped=True**,
with a zero command and the robot only 0.138 m from the placed ball. A new legal
exit routine cannot move during that observed pause; observation/referee timing
and earlier positioning remain relevant limitations.

## Code attempted, field players only

- `team/src/field_safety.py`: separate persistent restart state. A locked taker
  requests a lateral **power-1.5** pass to a designated different receiver at a
  1.8 m target, rather than shooting. The latch survives ball-free/timeout.
  The receiver becomes the only attacking roamer after the ball moves 0.7 m,
  and full-power attack requires ≥1.0 m displacement from the restart point.
  Release uses receiver proximity followed by further observed ball movement.
- Public Context has no authoritative touch events. Those geometry/proximity
  checks are **not proof of a physical second touch**. Referee data is used only
  offline; no private/event APIs, disk/network I/O or local restart-release timer
  were added to play().
- Opponent restarts: end any native task and issue fixed-heading body velocity
  along a radial escape toward ≥2.1 m clearance, with a boundary-intersection
  fallback when the radial target is outside the field. No path detour/rotation
  controller; speed capped at 0.65 m/s. Wait until official phase release.
- Normal support: after three seconds without 0.2 m movement inside the 3 m
  inactivity radius, slowly exit toward 3.65 m at 0.35 m/s, zero commanded yaw.
  Stay outside until the ball moves. This uses a local inactivity timer only,
  never a restart-release timer.
- `field_safety_params.py`: isolated constants. `field_logic.py`: field-only hooks.
  `tests/test_field_safety.py`: pass/handoff persistence, distinct receiver,
  displacement threshold, new restarts, missing partner/ball/game, empty players,
  radial direction, boundary constraints, clearance and inactivity escape.
  `test_team_dispatch.py`: updated intended pass/receiver expectations.

Keeper dispatch, Player, parameters, helpers, framework, telemetry implementation,
sample field primitives/parameters and official opponent remain unchanged from
merged V6. No shared Player API or keeper store/state was changed.

## Remaining incidents — unresolved, not hidden by the warning counter

Full referee events, latest snapshots, sampled pre-event windows and last active
snapshots are in **remaining-incidents.json**. Times below are referee simTime,
which includes setup time and can exceed 600 even in a 600-regulation-second game.

### One own-goal set-play warning

Game 07, **197.852 s**: `goal_disallowed_own_free_kick/own_goal_from_free_kick`.
Our goal kick was placed at (−6,2); player 3 was the first recorded toucher at
196.686 s, then ball-free, then the disallowed own goal. This was not a keeper
touch. A low-power lateral request did not guarantee a safe physical delivery;
the exact physical cause was not established. There were **zero** V7
`goal_disallowed_indirect` warnings and **zero opponent-restart retakes**, but this
remaining own-goal warning means restart safety is not solved.

### Five new kickoff positioning penalties

Game 04, player 3, at **115.418, 235.752, 291.108, 463.438 and 589.708 s**:
`illegalPosition/kickoff_kicking_side_outside_center`. The new receiver target
was on the halfway line and outside the center circle. The sample movement
controller let its body cross the referee's own-half tolerance (~5 cm), repeatedly
receiving 30-second penalties. The action was `restart:receive_position` in every
latest snapshot. This is a new bug in the attempted handoff, not a keeper issue.
It needs an own-half inset for kickoff receiving; it is deliberately not silently
patched after benchmarking, so the pushed source matches the tested candidate.

### Two inactive waiting receivers

Game 05/player 2 at **275.152 s**, game 06/player 2 at **92.470 s**:
`inactiveRobot`. Both public game states were already normal PLAYING, with
player 2 still at `restart:receive_position`, zero velocity/no native kick, while
player 3 remained in the native `restart:short_pass` session. Thus the new normal
support guard did **not** cover the pending receiver wait. No ordinary `support`
inactivity penalties were observed, but inactivity is not fully solved.

### Four fallen penalties and one SET-motion penalty

- Game 03/player 2, **288.466 s**.
- Game 04/player 3, **508.472 s**.
- Game 06/player 2, **374.192 s**.
- Game 06/player 3, **381.528 s**.

All four were field players. At penalty time three were recovering and one was
stopped, with zero/unaccepted velocity commands. The last non-recovery action
snapshots were 12–18 wall seconds earlier (attack, READY, support, attack). These
are too stale to establish the physical fall causes. Do not attribute them all
to radial escape, shuffle, native shooting or collisions without further evidence.

Game 01/player 2 also received `motionInSet` at **46.830 s**. The latest observed
action was stopped, native kick inactive, zero velocity requested but not accepted.
The rule failure is real; whether residual movement, mode/recovery latency or
observation timing caused it remains unverified.

## Checks and artifacts

```
Ran 97 tests in 0.018s

OK
```
```
PASS: 8 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 1 animations verified
```
```
PASS: keeper dispatch, Player, parameters, helpers, utilities, framework, telemetry, sample field primitives and opponent unchanged from merged v6
```

203,849 telemetry ticks and 1,604 native events parsed with no dropped records or
writer errors; 13,414 player-action samples used `support:inactive_escape`.
Telemetry flag remains off in source; runner enabled it via environment.

Unit command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`.
Validator: `python3 scripts/check_team_results.py --results match-results/set-plays-v7`.
Per-game results/events and complete source/package provenance are retained in
`batch-01/`. Raw `.gz`, PNG/WebP and agent packages remain local-only, not committed.

Time-lapse: `batch-01/match-01/evidence/match-timelapse.webp` (13 frames, 11.7 s,
139,532 bytes). `snapshot-final.png` was visually inspected: actual CPU-rendered
finished 4–3 match, 0.0 s. This is a time-lapse, not real-time video.

The Booster skill remains unavailable; this used basic repository rules and
actual referee evidence, not an official full audit. PR #6's failed-CI notification
was received before the merge notification; its CI loop was not delegated here
and was not investigated. This branch is a failed experiment, not merge-ready.
