# V8: throw-in-only handoff with active receiving wait

Branch **devin/set-plays-v8**, cut directly from `origin/main`
**4c58f084487b25028804b1c46428e6805b58b0bd** (merged V6). No PR opened.
Eight matches with telemetry enabled, four home/four away, two concurrently.
Every game ended naturally with `time_expired` after **600 regulation seconds**;
zero failed launches. Source stayed unchanged throughout the batch.

## Results against V6

Scores are **ours–sample**. Fall counts are referee penalties, not every physical fall.

| Game | Side | Score | Result | Our fouls | Our falls | Our set-play warnings |
|---|---|---:|---|---:|---:|---:|
| 01 | Home | 1–3 | Loss | 1 | 1 | 0 |
| 02 | Away | 2–1 | Win | 0 | 0 | 0 |
| 03 | Home | 2–3 | Loss | 1 | 0 | 1 |
| 04 | Away | 3–2 | Win | 0 | 0 | 0 |
| 05 | Home | 3–1 | Win | 2 | 0 | 2 |
| 06 | Away | 3–2 | Win | 0 | 0 | 0 |
| 07 | Home | 2–2 | Draw | 1 | 0 | 1 |
| 08 | Away | 3–3 | Draw | 0 | 0 | 0 |

| Candidate | Games | W/D/L | GF–GA | Mean GD | GF/game | GA/game | Our falls | Our warnings |
|---|---:|---|---|---:|---:|---:|---:|---:|
| V6 reference | 16 | 4/6/6 | 32–36 | −0.250 | 2.000 | 2.250 | 1 | 9 |
| V8 | 8 | **4/2/2** | **19–17** | **+0.250** | 2.375 | 2.125 | 1 | 4 |

Mean GD improves by **0.50/game** in this eight-game sample. This is not a claim
of a statistically established improvement or a clean safety result: V8 still
has one fall and four opponent-restart violations. The fall rate is **1/8** versus
V6's **1/16**, not fewer. Warning rates are 4/8 versus 9/16; raw counts alone are
not comparable across different sample sizes. One requested batch was run.

### Own set-play warnings by type

| Type / reason | V6, 16 games | V8, 8 games |
|---|---:|---:|
| `goal_disallowed_indirect` / `indirect_goal_requirement_not_satisfied` | 6 | **0** |
| `set_play_retake` / `free_kick_avoidance_radius` | 2 | **4** |
| `set_play_retake` / `defender_set_play_interference` | 1 | **0** |
| Disallowed own goal from a free kick | 0 | **0** |
| **Total** | **9** | **4** |

V8's four avoidance retakes were three goal-kick incidents and one throw-in.
There were **zero inactivity penalties**, including zero waiting-receiver ones.
There were no V7-style kickoff positioning penalties: the kickoff was not changed.

## Focused implementation

- `team/src/throw_in.py`: ports only V7's short-pass/designated-receiver handoff.
  It starts only on **our SetPlay.THROW_IN**, never on kickoffs, goal kicks,
  direct/indirect free kicks, corners, penalties or opponents' restarts.
  The taking robot requests a lateral power-1.5 pass toward a fixed 1.8 m
  receiving target. After 0.7 m ball displacement the other roamer takes over;
  full-power attack requires at least 1.0 m from the restart origin.
  The latch survives official ball-free/expiry until the receiving handoff
  completes or another stoppage/restart supersedes it.
- Waiting receiver: shuttles between two targets ±0.55 m along the field x-axis,
  capped at **0.25 m/s**, acceleration **0.6 m/s²**, zero commanded yaw.
  Endpoint hysteresis reverses the shuttle without parking. The receiving area
  is inset to keep both endpoints inside the field. Within 3.3 m of the ball,
  it uses translational commands instead of a planner's stationary arrival or
  turn-only wait. Farther away, it uses the stock robot/ball-avoiding approach.
  This continues after ball-free and does not use a timer to release a restart.
- `throw_in_params.py`: isolated constants; no shared/keeper parameter edits.
- `field_logic.py`: one interceptor before the original phase handlers. The
  original handlers themselves remain AST-identical to V6.
- `tests/test_throw_in.py`: all restart types/teams, original kickoff command,
  ball-free persistence, designated second robot and displacement gate,
  continuous idealized receiver motion over 30 seconds, bounded endpoints,
  near-ball approach, other restarts, stopped/missing game/ball and empty roster.

No V7 opponent escape controller, normal-support inactivity guard, kickoff
handoff, goal-kick handoff or free-kick handoff was carried over. Original keeper
dispatch, Player, parameters, helpers, utilities, framework, telemetry, sample
field primitives/parameters and official opponent remain byte-identical to V6.
The only store addition is private field-player handoff memory. Public Player
and main entry signatures are unchanged.

The public Context does not expose authoritative referee touch events. The
handoff uses a distinct receiver plus observed ball displacement/proximity, not
a private subscription or I/O from play(). It does not prove physical contact
merely because a persistent native kick session was requested.

## Receiver telemetry: no idle commands, but physical stalls remain possible

186,537 ticks and 1,768 native events parsed with no dropped records or writer
errors. There were **8,670 waiting-receiver samples**; **6,882** were within 3 m
of the ball. Every one of those near-ball samples had a nonzero translational
command accepted by the backend velocity gate, with no rejected commands.

**Command acceptance is not proof of physical movement.** The actual pose stream
still contains stall/contact windows. The maximum dwell within 0.2 m of an anchor
was **65.20 wall seconds**, spanning mostly an exclusive throw-in and then some
ball-free time. Restricted to normal, ball-free play, the maximum was **9.46 wall
seconds** (six seconds of referee remaining-time change). Neither produced an
inactivity penalty in these games, but this does not establish that a receiver
can never be physically blocked or will never trip inactivity in another game.

At the start of the long dwell, an opponent was about 0.415 m from the receiver;
the normal-play example had a teammate about 0.324 m away. Physical obstruction
is plausible, but no contact sensor evidence was collected, so the exact cause
is unverified. To challenge a blanket low-speed/deadband explanation, other
same-command waiting windows were checked: one moved **0.865 m over ~2 wall
seconds** while the requested speed remained approximately 0.25 m/s. That does
not isolate propulsion from external contact either. Do not equate nonzero
commands with a guarantee of uninterrupted physical movement.

See `receiver-dwell-contexts.json` for first/last snapshots of the worst windows
and a moving comparison, and `telemetry-coverage.json` for sample counts.

## Remaining referee incidents

`incident-contexts.json` contains event evidence, latest snapshots, sampled
pre-event windows and last active snapshots. Times are referee simTime, including
setup time, rather than only the 600-second regulation clock.

- Game 01, **467.828 s**, player 3: `fallenRobot`. Last non-recovery action was
  attack 17.61 wall seconds earlier; this is too stale to establish the physical
  fall trigger. It was a field player, not the unchanged keeper.
- Game 03, **41.284 s**, player 2: opponent goal-kick avoidance retake; distance
  **1.194 m**, observed action `opp_set:retreat`, x≈7.162 beyond the endline.
- Game 05, **62.224 s**, player 2: opponent goal-kick avoidance retake; distance
  **1.206 m**, `opp_set:retreat`, x≈7.101 beyond the endline.
- Game 05, **65.632 s**, player 3: another opponent goal-kick avoidance retake;
  distance **1.428 m**, observed `opp_set:retreat`.
- Game 07, **285.614 s**, player 3: opponent throw-in avoidance retake; distance
  **0.770 m**, latest observed action `recovering` rather than an active retreat.

Opponent escape behavior was deliberately left unchanged. These are the same
category of failures already seen in V6, but it is not established that the
incidents are causally unrelated to changed teammate/ball positions from V8.

## Checks and retained evidence

```
Ran 96 tests in 0.040s

OK
```
```
PASS: 8 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 1 animations verified
```
```
PASS: v6 keeper, field primitives, parameters, normal support and all original phase handlers unchanged; no v7 escape/inactivity controller carried over
```

Commands:
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/check_team_results.py --results match-results/set-plays-v8
```

Results, events, summaries and source/package provenance: `batch-01/`.
Numerical aggregate: `aggregate.json`. Exact output: `unit-tests.txt`,
`validation.txt`, `scope-audit.txt`, `build-output.txt`.

Time-lapse: `batch-01/match-01/evidence/match-timelapse.webp`.
Final snapshot: `batch-01/match-01/evidence/snapshot-final.png`, visually inspected
as an actual CPU-rendered finished 1–3 match, 0.0 s. This is a time-lapse, not
real-time video. Raw gzip telemetry, images, packages, certificates and keys are
local-only and not committed. Artifacts are mirrored into the primary repo's
`match-results/set-plays-v8/`. The Booster skill remains unavailable, so these
are basic repository/rules checks plus actual referee evidence, not an official
full rules audit. This branch is pushed as requested, with no PR or merge.
