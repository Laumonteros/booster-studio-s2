# Main telemetry: evidence before candidate v5

Base: `origin/main` e2db7d9 (PR #4 keeper). The two fully instrumented games
are `batch-02`, one home and one away, both natural 600-second regulation
finishes. No strategy changes were made. SDK/backend probes are diagnostic
only; no policy reads their private state. Keeper decisions/parameters and
the platform framework/opponent are untouched.

## Reproduce / collect

Telemetry is **off by default**: `team/src/param.py:TELEMETRY_ENABLED=False`.
For the observed runs, set it to `True`, build with `scripts/build_team.sh`,
and run `scripts/run_team_batch.py --matches 2 --workers 2 --telemetry`
with the normal package/output/work arguments. Restore `False` afterwards.
`ROAMER_TELEMETRY_FILE` also opts in when the agent launcher preserves that
environment variable. Container-level environment injection alone has not
been independently verified through the proprietary agent launcher.
Default output is `/tmp/roamer-telemetry.jsonl` **inside the runtime container**.
The runner copies it after shutdown and writes `match-XX/telemetry.jsonl.gz`.
Raw files remain available under `/home/ubuntu/booster-studio/main-telemetry-runs/`.
Compressed traces and image/video captures are local-only, ignored artifacts;
the reproducible source snapshots, results, referee events, numerical analysis
and selected complete tick/event contexts are committed as text.

Commands:
```
python3 scripts/analyze_telemetry.py match-results/telemetry/batch-02
python3 scripts/check_team_results.py --results match-results/telemetry
```

Instrumentation queues snapshots without filesystem/network I/O in `play()`;
a bounded asynchronous writer serializes JSONL. Native start/stop requests,
successes and errors include robot, calling thread, pose, ball and the
thread-local high-level action/call stack. Velocity `accepted` means it passed
the backend's local walk/not-kicking gate, **not** a native acknowledgement.
Attack/walk call arguments carry chosen targets; backend commands carry actual
body-relative velocity/direction, power and ball coordinates.

The initial `batch-01` is a **pilot, not part of the task-transition analysis**:
the framework assigns backends *after* constructing players. A constructor-only
probe recorded ticks but missed backend/native commands. This was caught live,
fixed with late-backend assignment instrumentation and a regression test, and
the home/away pair was repeated. Both pilot games nevertheless finished normally
(1–3 each; one own fall and one own warning across the pair). They are retained,
not silently discarded as failed launches or mixed with the analysis pair.

## Counts and definitions

Scores below are ours–sample. A reach episode enters within **0.7 m** of the
observed ball and resets beyond **1.2 m**. This is a proximity proxy, not proof
of foot contact. Percentages use that game's observed PLAYING/non-stopped ticks.
Possession is a referee-touch interval: our first touch until opponent touch,
placement, goal or match end. It can include keeper touches; it is not exclusive
physical control. SDK sessions overlapping each interval count once each.

| Measure | Home / match-01 | Away / match-02 |
|---|---:|---:|
| Score | 0–4 | 2–5 |
| Own fouls / fallen penalties / warnings | 1 / 0 / 1 | 0 / 0 / 0 |
| Logged ticks / PLAYING ticks | 23,826 / 17,598 | 22,516 / 14,592 |
| Roamer 2 reach episodes / near-ball tick % | 31 / 9.40% | 31 / 9.46% |
| Roamer 3 reach episodes / near-ball tick % | 28 / 6.42% | 13 / 3.97% |
| Referee-touch possessions | 41 | 30 |
| Roamer SDK sessions | 56 | 46 |
| Sessions per possession, mean / max | 1.341 / 5 | 1.300 / 3 |
| Kick-command updates (not separate kicks) | 9,849 | 7,607 |
| Session median duration | 5.312 s | 4.608 s |
| Sessions shorter than 1 s | 4 | 3 |
| Ended by attack-range release | 43 | 33 |
| Ended by support/role handover | 11 | 4 |
| Ended by READY / STOP | 1 / 1 | 3 / 6 |
| Native errors / dropped / malformed records | 0 / 0 / 0 | 0 / 0 / 0 |
| Median support distance from ball | 3.858 m | 3.816 m |
| Close, in-range full-power goal-aim updates | 679 | 304 |
| Those updates with an opponent within 0.45 m of requested lane | 516 (76.0%) | 302 (99.3%) |
| SDK virtual aim ray outside ±1.25 m goal mouth | 128 (18.9%) | 14 (4.6%) |
| Shooting possessions / scored within possession | 14 / 0 | 5 / 1 |
| Shooting possessions initially lane-blocked | 11 / 14 | 5 / 5 |

The SDK API is a **persistent soccer-control session**, not a future for a
single kick. `start()` enables it; updates change its virtual goal/ball; `stop()`
disables it. Source inspection found no exposed individual-kick completion or
physical shot event. Thus **all 102 observed roamer session ends were requested
by our code**, and there were no autonomous session-end notifications. This does
**not** mean 102 physical kicks or zero completed physical kicks. Exact physical
attempts/completed-kick counts are unavailable. The table reports session starts
and command updates separately rather than inventing that distinction.

We specifically tried to disprove the previous churn hypothesis: only 7/102
sessions were under 1 s, with 4.6–5.3 s medians. Main does not reproduce the
sub-second churn of the rejected roamer candidates. Role handovers do terminate
15 sessions, but churn is **not supported as the dominant main regression**.
There were only seven tick gaps over 200 ms across 46,342 ticks; maximum start
call latency was 82 ms. These are descriptive observations, not an A/B overhead
measurement against uninstrumented main.

## Three biggest fixable causes, ranked

### 1. Blind goal-lane choice / loss of goal-aim geometry

**Verified reachable policy defect:** `main.play` calls `Player.attack` with
`tactics.shot_target`; that function sees only field, ball and restart origin,
not opponents. The recorded calls and actual backend `kick_body` updates prove
this path ran. Among near-ball (≤1 m), in-range (≤4.5 m), full-power (≥5),
goal-target updates, **818/983 (83.2%)** had an observed opponent within 0.45 m
of the requested segment; **16/19** shooting possessions began in such a lane.
Only one of these 19 possessions scored before the opponent next touched/reset.

The native manager's inspected `update_command` implementation projects its
virtual goal **8 m from the robot**, whereas `Player.attack` derives direction
from **ball to target**. With the robot off that line these are different rays:
the reconstructed ball→SDK-virtual-goal ray misses the conservative goal mouth
in **142/983 updates**. This reconstruction uses public observed poses and the
inspected SDK geometry, not simulator internals.

**Not established:** there is no physical shot trigger/foot contact trajectory
callback. Frame counts are correlated command samples, not independent missed
shots. A blocked requested lane does not prove that exact robot blocked an actual
shot; learned gait can move before kicking. Observation/odometry differences
and proprietary motor execution remain unverified links. The facts justify a
targeted lane-aware/aim-geometry candidate, not a claim that 83% of shots failed
for this reason. Falsification is the v5 benchmark, keeping baseline approach
thresholds, gait and session timing rather than reintroducing alignment churn.

### 2. Support is too far from the next contest

The active main path always calls `support_target`, whose 3.3 m lateral and
1.9 m trailing offsets generate the recorded support targets. Median actual
distance is 3.82–3.86 m. At **all nine conceded goals**, support is away from
the immediate goal-mouth contest (see below), often still travelling/turning.
This is verified positioning, not proof that a particular closer position
would have prevented a goal. Deep support may protect other situations; no
counterfactual was run. Do not silently change keeper movement to compensate.

### 3. Opponent restart escape aims too far before clearing the legal radius

At home sim 436.236 s player 2 was only **~1.17 m** from the goal-kick ball,
already executing `restart:clearance`; it was not still running an attack task.
The next retake was at 436.256 s. `retreat_target` seeks the >3.2 m inactivity-safe
waiting circle; near the endline/sideline that circle's feasible nearest point
is strongly lateral. The recorded immediate target (5.991,3.084), from robot
(6.449,2.884) around ball (5.986,1.813), and actual body command
(-0.687,-0.301,0), yaw -0.826, produce almost zero outward radial speed.
This directly disproves 'a lingering native kick caused this violation': the
probe records walk mode, no active kick and actual accepted retreat velocity.
The reachability chain is phase→their_restart→retreat_target→short waypoint→walk,
confirmed by source and that tick. A two-stage immediate legal-radius escape,
then inactivity-safe wait route, addresses the observed geometric defect.
Public state/ball-placement latency may also contribute and has not been isolated.

Own restart aim changed from a short pass to a goal target within a live native
session 10/12 times, but **neither analyzed game had our disallowed restart goal**.
Do not present that plausible prior failure as a cause proved by this pair.

## Every conceded goal and set-play violation

All coordinates below are team-normalized. `attack` targets were (7.25,±0.75);
support targets were (-5.5, offset-y) when the ball was by our goal. Full exact
poses, targets, velocities, kick parameters and preceding 1/2-second snapshots
are in each `match-XX/telemetry-analysis.json:event_contexts`.

| Game / referee sim seconds | Keeper | Roamer 2 | Roamer 3 | Prior snapshot age |
|---|---|---|---|---:|
| H / goal 56.076 | track (-6.58,-0.22) | support (-2.73,0.18) | attack (-5.51,-1.66) | .001 s |
| H / goal 197.386 | track (-6.68,0.06) | attack (-4.15,-1.27) | support (-3.82,2.55) | .031 s |
| H / goal 315.986 | track (-6.64,-0.75) | attack (-4.78,-0.41) | support (-5.61,2.18) | .066 s |
| H / illegalPosition 436.236 + retake 436.256 | stopped in clearance (-6.55,0) | clearing (6.45,2.88), body velocity (-.687,-.301,0) | clearing (3.91,1.14), body velocity (-.281,-.695,0) | .028/.016 s |
| H / goal 550.146 | track (-6.67,0.91) | support (-.02,-1.91), turning | attack (-.86,.96), turning | .010 s |
| A / sample disallowed indirect 89.256 | track (-6.60,1.00) | support (-2.02,1.03) | attack (-3.43,2.01) | .130 s |
| A / goal 220.376 | track (-6.67,.45) | support (-3.56,-.88) | attack (-4.86,.57) | .049 s |
| A / goal 316.664 | track (-6.82,-.32) | support (-5.52,-3.18), turning | attack (-7.34,.32), native kick | .016 s |
| A / goal 441.636 | track (-6.76,-.36) | support (-5.52,2.30) | attack (-6.93,-.93), native kick | .003 s |
| A / goal 522.120 | track (-6.61,-.07) | attack (-4.82,-.73) | support (-5.49,2.39) | .001 s |
| A / goal 623.286 | track (-6.18,.16) | attack (-5.98,-1.37), native kick | support (-5.33,2.77) | .013 s |

These are latest **prior observed** actions, not omniscient instantaneous physical
states. In three away concessions an attacker still had a native task at/behind
the goal line; no claim is made that it scored an own goal without a referee
touch/trajectory causal chain. Keeper behavior is reported, not modified.

## v5 decision

Target the #1 shooting defect without changing baseline approach/session lifetime,
plus #3 legal-radius escape as a necessary zero-warning safeguard. Leave support
and all keeper logic unchanged to avoid a broad, confounded controller rewrite.
Gate against the provided **main −2.0 mean GD / zero wins**, not this small pair:
8 alternating-side matches, mean GD ≥−0.5, ≥1 win, zero own fallen penalties and
set-play warnings; run another eight if just at/near the acceptance boundary.
Results will be recorded separately under `match-results/roamers-v5/`.
