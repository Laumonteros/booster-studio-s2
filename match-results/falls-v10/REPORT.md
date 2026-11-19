# V10: crowded normal-attacking walking speed

Branch `devin/falls-v10` from `origin/main` at
**ff2de4b7afd02b5a754333164131d4048956b634** (merged V9).
Eight complete matches, alternating four home/four away, two concurrently,
telemetry enabled. All ended naturally with `time_expired` after **600 regulation
seconds**; zero failed launches. Source stayed unchanged throughout the batch.

## Result against V9

Scores are **ours–sample**. Fall counts mean referee fallen penalties, not every
physical fall or every SDK recovery episode.

| Game | Side | Score | Result | Our fouls | Our falls | Our set-play warnings |
|---|---|---:|---|---:|---:|---:|
| 01 | Home | 4–2 | Win | 1 | 1 | 0 |
| 02 | Away | 2–2 | Draw | 0 | 0 | 0 |
| 03 | Home | 2–2 | Draw | 2 | 0 | 0 |
| 04 | Away | 1–4 | Loss | 0 | 0 | 0 |
| 05 | Home | 1–2 | Loss | 0 | 0 | 0 |
| 06 | Away | 2–2 | Draw | 0 | 0 | 0 |
| 07 | Home | 3–2 | Win | 0 | 0 | 0 |
| 08 | Away | 3–1 | Win | 0 | 0 | 0 |

| Candidate | Games | W/D/L | GF–GA | Mean GD | Roamer falls | Our warnings | Our fouls |
|---|---:|---|---|---:|---:|---:|---:|
| V9 | 8 | 4/2/2 | 21–16 | +0.625 | 2 | 1 | 6 |
| V10 | 8 | **3/3/2** | **18–17** | **+0.125** | **1** | **0** | **3** |

Observed fallen penalties decrease **2 → 1**, but scoring, mean GD and wins
regress. Mean GD is **0.50/game worse**. This is not a clearly better team or
proof that the cap caused the lower fall count; one requested batch was run.

### Own warnings by type

| Type / reason | V9 | V10 |
|---|---:|---:|
| `set_play_retake` / `free_kick_avoidance_radius` | 1 | **0** |
| … opponent goal kick | 0 | 0 |
| … opponent throw-in | 1 | 0 |
| Defender-interference retake | 0 | 0 |
| Disallowed indirect goal | 0 | 0 |
| Disallowed own goal from free kick | 0 | 0 |
| **Total warning events** | **1** | **0** |

Zero warnings does **not** mean no positional penalties: game 03 had one
field-boundary penalty in SET, described below.

## Historical fall investigation

`baseline-fall-audit.json` retains per-fall referee events, lead-in snapshots,
requested-command measurements, last-active snapshots, counterexamples and a
replay of the actual V10 guard over the four source games. Raw inputs remain
under V6/V8/V9's original telemetry paths.

### Method and limits

The last pre-penalty snapshot was not treated as the cause. Penalties occurred
**10.65–17.61 wall seconds after the last non-recovery action** in these cases.
The audit uses a five-wall-second window ending at that last active sample,
before the sustained recovery interval. This is an **onset proxy**, not an
authoritative physical fall time: `recovering` combines fall/get-up/mode states,
and asynchronous backend gating can change inside a tick.

The logs expose requested chassis commands, poses, nearby robot projections and
persistent native kick updates. They do not contain contact impulses, roll/pitch,
or the native soccer controller's internal chassis/foot commands. A native kick
direction is **not** a measured yaw rate, and a kick update is not a completed
physical kick. Projected robot proximity is not proof of body contact.

### Findings per fall

| Fall | Verified lead-in | Interpretation and limits |
|---|---|---|
| **V6 batch 01/game 05/player 2**, simTime 61.808 s | Opponent goal-kick retreat beside the endline/post; requested speed up to **0.75 m/s** and yaw up to **2 rad/s**. Closest robot **0.557 m**. No kick updates in the five-second lead-in. Last active action preceded penalty by 10.65 wall s. | Rotating exit near post/robots, not a normal attacking sprint. Physical post/body contact is unverified. This old exit no longer executes in V9/V10: V9 already replaced it with zero-yaw translation. Therefore it is **not** justification for changing the protected current exit. |
| **V8 game 01/player 3**, simTime 467.828 s | Normal attack changed from native chasing to accepted **2.0 m/s** walking commands while opponent 3 was **0.270 m** away. Some samples place that opponent directly ahead. Walking continued through close proximity. Last active sample preceded penalty by 17.61 wall s. | Reachable high-speed, unavoided close-quarters walking is the strongest actionable exposure. Contact is consistent with the projections but not measured. There was no common visible body-command acceleration spike within the constant-speed walking run. |
| **V9 game 07/player 2**, simTime 272.760 s | Normal attack, mostly persistent native kick/chase updates at power 5; opponent distance fell to **0.296 m**. The observed ball later moved behind/lateral to the body while updates continued. A preceding walking interval requested 2.0 m/s. Last active sample preceded penalty by 11.12 wall s. | Close native contest, not evidence of a known chassis turn rate. Native gait/foot motion is unobserved. A public walking-speed cap can affect the preceding walk, **not directly limit the later native task**. No claim that this fall's mechanical cause is established or solved. |
| **V9 game 08/player 3**, simTime 188.684 s | Normal attack walked at **2.0 m/s** while turning near the own post, keeper and other roamer; minimum robot projection gap **0.259 m**. The trace later switched to turn-only commands. Last active sample preceded penalty by 11.48 wall s. | Another reachable crowded full-speed walking exposure. Teammate versus post contact versus an already-starting topple cannot be separated. An abrupt requested speed-to-turn transition was visible, but timing does not establish it as the physical trigger. |

### Evidence-ranked choice, not a universal mechanical diagnosis

1. **Targeted exposure: full-speed normal walking near another robot**, directly
   observed in two of the three recent V8/V9 falls. The source chain is
   `_act_normal → attack → walk_to → set_velocity`; these snapshots have action
   `attack`, public PLAYING/NONE/ball-free state and accepted chassis commands.
   Thus the new normal-only guard is actually reachable in those scenarios.
2. **Separate native-contest exposure**, observed in V9 game 07. Actual native
   turn/acceleration/contact remain unknown. No native kick change was made.
3. **Legacy rotating restart exposure**, V6 only, excluded because that command
   path was already replaced and current opponent exit is protected by scope.

To challenge a simplistic speed-equals-fall explanation, other samples in all
four source games were checked: **2,186** accepted attack-walking samples had
speed above 1.9 m/s and robot separation below 0.6 m **more than 40 wall seconds
from the listed penalty**. That does not exclude unpenalized recoveries, but it
shows the exposure is not sufficient to predict a fallen penalty. There is no
single confirmed mechanical root cause across all four events.

Adjacent requested body-velocity differences were also examined. V8 game 01 and
V9 game 07 had constant accepted walking requests between native intervals;
V9 game 08 showed a sharp requested speed-to-turn switch. Native intervals hide
the actual chassis trajectory, and command differences are not physical
acceleration. The evidence does not support a global acceleration/turn limiter.

## Minimal implementation

- `team/src/field_motion.py`: a pure public-Context velocity transform.
  **Only action `attack` in normal ball-free PLAYING** is eligible. Keeper ID 1,
  unknown context/pose, stopped/other states, ownership/set plays and kickoff
  clocks bypass it. Unknown neighbors are skipped; self is not an obstacle.
- Within **0.50 m** of any teammate/opponent, requested translational magnitude
  is capped at **0.75 m/s**. The cap blends continuously to the original 2.0 m/s
  maximum by **0.85 m**; beyond that, output is exactly unchanged. Direction,
  yaw, slower requests and stops are preserved. Side/behind neighbors count too,
  because the teammate-crowding case was not purely head-on.
- `field_motion_params.py`: three isolated constants, no shared parameter edits.
- `field_player.py`: exactly one import and one call at `set_velocity` entry.
  No class/interface/roster change. Native `kick()` does not use this chassis
  entry point and is unchanged. The helper does not introduce disk/network I/O,
  timers, strategy-state mutation or private SDK access.
- `tests/test_field_motion.py`: real Player/backend integration, both teams'
  neighbors, soft band/direction/yaw, free-running speed, slower/zero/turn-only
  commands, all protected actions/set plays/states, missing observations, keeper
  exclusion, self/unknown neighbors and unchanged native kick requests.
- The existing exact-source fidelity test permits **only the explicit two-line
  hook** in addition to the preexisting import isolation; it still compares the
  entire remaining Player, utilities and parameters against the sample.

Historical replay of the actual guard would change **4,913 requests** across
48,269 recorded attack ticks in those four games: **10.18% of all attack ticks**,
or **35.91% of accepted attacking chassis requests**. These totals include
restart attack ticks, which the actual guard bypasses. All **34,586 native kick
update samples** are outside the chassis transform. This is a targeted change,
but not proof that normal attack throughput is unaffected; this batch's scoring
regressed and a speed/contest tradeoff remains possible.

Keeper/main, throw-in handoff and parameters, opponent exit and parameters,
dispatch, roster, shared parameters, utilities, framework, telemetry and official
opponent are unchanged. Handoff actions remain bypassed even after ball-free.
No kickoffs, support or READY/STOPPED commands are modified.

## V10 observations and remaining fall

184,426 ticks and 1,648 native events parsed; no dropped records/writer errors.
All **9,222 crowded normal-attack accepted chassis samples** obeyed the cap;
8,700 were at its envelope. There were also **15,772 uncrowded full-speed
samples** and 62,478 normal native kick update samples, showing both untouched
paths remained active. These are command samples, not physical kick counts.

**Game 01/player 3 still fell**, simTime **77.700 s**. The lead-in included a
close native contest, followed by walking with the cap active. Requests were
0.75 m/s at very small projected separation; the last active request was
approximately **0.906 m/s and 0.656 rad/s** at 0.544 m separation. Opponent 1's
projected position nearly overlapped the player in an earlier sample. This may
reflect contact, a fall already underway, or projection effects; the exact
physical trigger remains unverified. The last active action was 13.21 wall
seconds before the penalty. **The cap works as implemented but does not eliminate
crowded/native/contact falls.** See `remaining-fall-window.json`.

Other own penalties in game 03:
- Player 2, **514.126 s**: inactivity during unchanged normal support, not a
  waiting throw-in receiver or newly capped attack.
- Player 3, **566.940 s**: `illegalPosition` / `field_boundary` in SET at
  x≈−7.731 m, beyond the 7.05 m tolerance. The latest public observation was
  READY and a 2.0 m/s READY command, a path the new guard bypasses. Its physical
  cause is not established; unchanged source does not prove causal independence
  from earlier altered match positions. No extra READY/normal-support fix made.

## Checks and retained evidence

```
Ran 112 tests in 0.045s

OK
```
```
PASS: 8 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 1 animations verified
```
```
PASS: keeper, throw-in handoff, opponent exit, dispatch, parameters, utilities and framework unchanged; sample field Player differs only by the explicit velocity-limiter import/call
```

Commands:
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/check_team_results.py --results match-results/falls-v10
```

`aggregate.json`, `baseline-fall-audit.json`, `incident-contexts.json`,
`remaining-fall-window.json`, `telemetry-coverage.json`, exact check/build logs,
and `batch-01/` retain analysis, events/results and source/package provenance.

Time-lapse: `batch-01/match-01/evidence/match-timelapse.webp`.
Snapshot: `batch-01/match-01/evidence/snapshot-final.png`, visually inspected as
an actual CPU-rendered finished 4–2 match at 0.0 s. Animation validation:
14 frames, 12.6 s, 140,514 bytes. Raw gzip telemetry, images/animation and packages
remain local-only; no keys/certificates committed. Artifacts mirrored under the
primary repo's `match-results/falls-v10/`. The full Booster rules skill remains
unavailable; these are basic repo/rules checks and actual referee evidence.
Branch pushed as requested; no PR or merge.
