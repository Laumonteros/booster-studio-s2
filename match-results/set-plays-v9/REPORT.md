# V9: opponent set-play clearance only

Branch `devin/set-plays-v9`, cut from `origin/main` at
**64de57af7c645c95f5dddf1c5de47009dc83b8be** (merged V8).
Eight full matches with telemetry, alternating four home/four away, two
concurrently. Every match ended naturally with `time_expired` after 600 regulation
seconds. Zero failed launches. No source changes during the batch.

## Result against V8

Scores are **ours–sample**. Falls are referee penalties, not every physical fall.

| Game | Side | Score | Result | Our fouls | Our falls | Our set-play warnings |
|---|---|---:|---|---:|---:|---:|
| 01 | Home | 2–4 | Loss | 1 | 0 | 0 |
| 02 | Away | 4–0 | Win | 1 | 0 | 0 |
| 03 | Home | 3–1 | Win | 0 | 0 | 0 |
| 04 | Away | 3–0 | Win | 0 | 0 | 0 |
| 05 | Home | 0–4 | Loss | 1 | 0 | 1 |
| 06 | Away | 4–2 | Win | 0 | 0 | 0 |
| 07 | Home | 2–2 | Draw | 2 | 1 | 0 |
| 08 | Away | 3–3 | Draw | 1 | 1 | 0 |

| Candidate | Games | W/D/L | GF–GA | Mean GD | Our falls | Our warnings | Our fouls |
|---|---:|---|---|---:|---:|---:|---:|
| V8 | 8 | 4/2/2 | 19–17 | +0.250 | 1 | 4 | 5 |
| V9 | 8 | **4/2/2** | **21–16** | **+0.625** | **2** | **1** | **6** |

Mean GD improves by 0.375/game in this batch. W/D/L is unchanged. Retakes
decrease from four to one, but **the problem is not eliminated** and falls
increase from one to two. This is not a clean safety result or proof of a
statistically established performance improvement. One requested batch was run.

### Own set-play warnings by type

| Type / reason | V8 | V9 |
|---|---:|---:|
| `set_play_retake` / `free_kick_avoidance_radius` | 4 | **1** |
| … opponent goal kick | 3 | **0** |
| … opponent throw-in | 1 | **1** |
| `set_play_retake` / `defender_set_play_interference` | 0 | 0 |
| Disallowed indirect goal | 0 | 0 |
| Disallowed own goal from a free kick | 0 | 0 |
| **Total warnings** | **4** | **1** |

## V8 root-cause audit and disproof checks

The four source contexts are retained in V8's `incident-contexts.json`.
`v8-retake-audit.json` extracts actor, public phase, native ownership, actual
action, requested target/velocity, and commanded world/radial velocity.
Raw V8 telemetry was also checked across phase transitions, not just the final
snapshot, to distinguish wrong dispatch from unsuccessful execution.

1. **Game 03, 41.284 s, player 2, opponent goal kick: ineffective/late exit.**
   It was already near the new ball placement beyond the endline. The public
   unpaused goal-kick phase dispatched `opp_set:retreat` about 4.8 wall seconds
   before the warning, not attack/support. Native kick ownership was false and
   velocity commands passed the backend gate. The boundary-circle target sent
   it toward the post/mouth instead of up the outside of the post. The last
   short target was approximately `(6.985, 1.258)` from `(7.162, 1.725)`;
   world velocity was toward negative y, initially **0.097 m/s inward radially**.
   It stayed only 1.194 m from the ball. `walk_to(face=ball)` also commanded up to
   2 rad/s rotation earlier in the exit. The unsafe requested route and failure
   to clear are verified; physical post contact as the sole cause is **inferred,
   not confirmed**, because no contact sensor evidence was collected.
2. **Game 05, 62.224 s, player 2, opponent goal kick: prolonged ineffective exit.**
   It had been in `opp_set:retreat` for about 28.9 wall seconds, not a late phase
   transition. Final pose was `(7.101, 1.507)`, distance 1.206 m, with a target
   `(6.915, 1.043)` leading through the nearby lower-y post corridor.
   The final radial command was only +0.030 m/s despite a 0.75 m/s body command.
   Again, there was no live native kick session. The observed route is a verified
   defect; whether post contact, gait response or another physical interaction
   dominated the stall is unverified.
3. **Game 05, 65.632 s, player 3, opponent goal-kick retake: insufficient buffer.**
   This robot had actually exited and waited around 1.57 m away. The old stop
   threshold was 1.5 m: only 5 cm above the rule's 1.45 m line. After the first
   retake it correctly stopped throughout the public paused interval. The ball
   moved toward it, and at the next assessment its gap was 1.428 m. It had only
   about 0.32 wall seconds of renewed active exit opportunity. The last outward
   command was +0.334 m/s. This was not support continuing to choose a point
   inside the active restart radius; it was loss of a small waiting margin plus
   too little available exit time after the official pause.
4. **Game 07, 285.614 s, player 3, opponent throw-in: no available exit actor.**
   On resumption it immediately entered `recovering`, remained there about eight
   wall seconds, and was excluded by main's `ensure_ready()` gate before field
   dispatch. Its velocity commands were rejected and it stayed 0.770 m away.
   This is verified from the dispatch gate and trace; the precise underlying
   fall/get-up/mode-switch condition is **not exposed in these tick records**.
   No radial/path-planning change can move it while that filter excludes it.

The active-player hypothesis was explicitly challenged: all three goal-kick
incidents had the opponent-set-play dispatcher running and native kick ownership
off, ruling out a lingering attack/support branch or persistent native kick as
their immediate command source. The fourth did **not** execute the exit branch.

## Focused fix

- `team/src/opponent_exit.py`: only called from `_act_opp_set_play`.
  For a goal-kick defender beyond the endline alongside/outside a post, the
  in-field waypoint goes toward the **same-side touchline**, not back through
  the post corridor. Other positions retain the radial/boundary-circle target
  construction. Already-inside actors may briefly reduce radial clearance on
  the post-safe detour; it is not falsely described as a monotonic radial exit.
- Body-frame translation is derived directly from the world exit vector at
  **0.75 m/s**, with **zero commanded yaw**. This removes face-the-ball rotation
  and near-target proportional slowdown while still inside the rule radius.
  Native kick ownership is released first.
- `opponent_exit_params.py`: **2.0 m** clearance instead of stopping at 1.5 m,
  giving a 0.55 m margin over the documented threshold. Once clear, the player
  stops and waits for the official phase change; no local restart-release timer.
- `tests/test_opponent_exit.py`: the two recorded endline geometries and their
  mirrored cases, bounded waypoints, zero yaw and post-away translation,
  idealized exit timing, the third robot's too-small wait margin and ball shift,
  already-clear/radial/empty/missing observations, unchanged opponent kickoff,
  and preservation of the fourth actor's recovery filter.

**Scope limitation:** the V8 recovery-only case is deliberately not bypassed.
Fixing its underlying readiness/physical recovery would require work outside
this available-player clearance controller. STOPPED and recovery filtering remain
untouched, including the requirement to stop during the official pause.

V8's throw-in handoff and all its parameters are byte-identical. Keeper/main,
shared parameters, Player, framework, utilities, telemetry, field primitives,
normal play, kickoffs, READY, our restarts and all other field functions remain
unchanged. Only the opponent set-play handler delegates to the new helper.
No private simulator input, I/O in play(), or shared interface change was added.

## V9 telemetry and remaining incidents

196,055 ticks and 1,828 native events parsed; no dropped records or writer errors.
The new exit ran for 2,325 samples, including **434 post-corridor goal-kick
samples**, so the special route was actually exercised. No own goal-kick retakes
occurred, but this does not prove the exact old physical scenes were replayed.

**One active-player throw-in exit is still too slow physically:** game 05,
**212.098 s**, player 2. It was in the correct unpaused opponent throw-in branch,
not recovering, with native kick inactive and accepted 0.75 m/s, zero-yaw
commands directed outward. Over **2.492 wall seconds** before the warning,
measured separation increased only **0.799 → 1.136 m**, below 1.45 m. This is a
late physical clearance, not a requested path into the circle or support target
inside it. Why physical translation was so much slower than requested remains
unverified; these logs cannot distinguish locomotion response, latency and all
physical interactions. See `remaining-retake.json` for first/last evidence.

Other own penalties:
- Game 01, player 2, **472.892 s**: inactivity while performing unchanged normal
  support, not receiving a throw-in or clearing an opponent restart.
- Game 02, player 2, **49.352 s**: motion in SET; last observed action stopped.
- Game 07, keeper/player 1, **207.666 s**: `stopped_motion`; keeper source was
  not changed. Zero commands do not prove physical immobility.
- Game 07, player 2, **272.760 s**: fallen penalty; last active action attack
  about 11.12 wall seconds earlier.
- Game 08, player 3, **188.684 s**: fallen penalty; last active action attack
  about 11.48 wall seconds earlier.

The fall snapshots are too stale to establish physical causes. Untouched command
paths do not prove incidents are causally unrelated to changed match positions.
No extra normal-play, keeper, recovery or stop-policy fixes were made.

## Checks and artifacts

```
Ran 102 tests in 0.046s

OK
```
```
PASS: 8 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 1 animations verified
```
```
PASS: v8 keeper, throw-in handoff, field primitives, shared parameters, normal play, kickoffs and all field functions except opponent set-play exit unchanged
```

Commands:
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/check_team_results.py --results match-results/set-plays-v9
```

`aggregate.json`, `v8-retake-audit.json`, `incident-contexts.json`,
`remaining-retake.json`, `telemetry-coverage.json`, `scope-audit.txt`,
`unit-tests.txt`, `validation.txt`, `build-output.txt`, and `batch-01/` retain the
analysis, exact checks, results/events and source/package provenance.

Time-lapse: `batch-01/match-01/evidence/match-timelapse.webp`.
Final snapshot: `batch-01/match-01/evidence/snapshot-final.png`, visually inspected
as an actual CPU-rendered finished 2–4 match at 0.0 s. Raw gzip telemetry,
images/animation and packages remain local-only; certificates/keys are not
committed. Artifacts are mirrored under the primary repository's
`match-results/set-plays-v9/`. The Booster skill is still unavailable, so this
is a basic repo/rules check with referee evidence, not an official full rules
audit. Branch pushed as requested; no PR or merge.
