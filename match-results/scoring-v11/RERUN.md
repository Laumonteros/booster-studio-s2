# Unchanged V11 rerun: batch 03 and 16-game comparison

Branch `devin/v11-rerun`, cut from merged main
**0de1ede24d2bec2bbc742265c946ad8e7e2ed5ef**. No strategy, framework,
parameter, test or harness changes. This report supersedes the first-batch
performance inference in `REPORT.md`, while retaining that historical report.

All 36 team source/config snapshot entries are identical between V11 batches
02/03 and merged main. The exact same signed package was reused, SHA256
`ab196eff70158e6ed552782da33a8ce0c9271222eda0b648499ae05cb74232c4`.
Simulator image, official sample revision and two-worker concurrency are also
identical. Details: `rerun-provenance-check.txt`, batch provenance/source files.

## New batch: eight complete regulation games

Telemetry enabled; alternating home/away; no failed launches or replacements.
Each match ended naturally after 600 regulation seconds. Scores are ours–sample.
Falls below mean **referee fallen penalties**, not every physical fall/recovery.

| Game | Side | Score | W/D/L | Our penalties | Falls | Own warning events |
|---|---|---:|---|---:|---:|---:|
| 01 | Home | 1–3 | Loss | 2 | 0 | 0 |
| 02 | Away | 4–2 | Win | 2 | 1 | 1 |
| 03 | Home | 2–4 | Loss | 0 | 0 | 0 |
| 04 | Away | 2–1 | Win | 0 | 0 | 0 |
| 05 | Home | 1–2 | Loss | 1 | 0 | 1 |
| 06 | Away | 2–2 | Draw | 0 | 0 | 0 |
| 07 | Home | 2–2 | Draw | 0 | 0 | 0 |
| 08 | Away | 3–4 | Loss | 0 | 0 | 0 |

Batch 03 penalties: two inactivity penalties (game 01, players 2/3), defender
restart interference (game 02, player 3), one fallen penalty (game 02, player 2),
and one illegal-position penalty (game 05, player 3). Warning events were a
defender-interference retake in game 02 and an avoidance-radius retake in game 05;
both opponent throw-ins. Events retained in `rerun-incidents.json`. No fixes made.

## Aggregates against V9's 16 games

| Team / batch | Games | W/D/L | GF–GA | Mean GD | GF/game | GA/game | Falls | Own warnings |
|---|---:|---|---|---:|---:|---:|---:|---:|
| V9 combined | 16 | 8/3/5 | 37–28 | +0.5625 | 2.3125 | 1.7500 | 3 | 2 |
| V11 first, batch 02 | 8 | 6/1/1 | 20–9 | +1.3750 | 2.5000 | 1.1250 | 0 | 1 |
| V11 rerun, batch 03 | 8 | 2/2/4 | 17–20 | −0.3750 | 2.1250 | 2.5000 | 1 | 2 |
| **V11 combined** | **16** | **8/3/5** | **37–29** | **+0.5000** | **2.3125** | **1.8125** | **1** | **3** |

V11 and V9 now have **the same W/D/L and goals scored**. V11 conceded one more
goal, so mean GD is **0.0625/game lower**. The first batch's scoring improvement
did **not** hold up over 16 games. V11 has fewer fallen penalties (1 vs 3), not
proof of fewer physical falls. No statistically established scoring benefit is
claimed. This rerun is evidence of substantial batch variance, not a diagnosis
of which match interactions caused the performance difference.

### Warnings by type

| Type / reason | V9: 16 | V11 batch 03: 8 | V11 combined: 16 |
|---|---:|---:|---:|
| `set_play_retake:free_kick_avoidance_radius` | 1 | 1 | 1 |
| `set_play_retake:defender_set_play_interference` | 0 | 1 | 1 |
| `goal_disallowed_indirect:indirect_goal_requirement_not_satisfied` | 1 | 0 | 0 |
| `ball_reset:clear_stuck_ball` | 0 | 0 | 1 |
| **Total** | **2** | **2** | **3** |

V11's stuck-ball advisory was in the first batch, attributed to the unchanged
keeper. Excluding that non-penalty advisory, V11 and V9 each recorded **two own
rule-warning events** over 16 games. All other own warning types are zero.

## New batch's lane-obstruction proxy

Same method as the first V11 batch: normal PLAYING, not stopped, no set play,
no kickoff ownership/countdown; attacking field player; ball before the goal
plane and within 4.5 m of (7,0); player within 0.8 m of the ball; `kick_body`
request present. Public normalized poses and the body-relative command reconstruct
the requested field direction and its intersection with goal plane x=7.

An observed opponent center within **0.45 m** of the ball-to-goal-plane segment
marks the lane obstructed. The counterfactual original center ray aims toward
**(7.25,0)**, projected onto the same plane, on the **same V11 snapshots**.
Requests are repeated native-task updates, **not independent physical shots**.

| Close in-range request proxy | First V11 batch | New V11 batch |
|---|---:|---:|
| Request samples | 5,309 | **4,992** |
| Selected lane obstructed | 2,259 (42.55%) | **2,189 (43.85%)** |
| Original-center ray obstructed, same snapshots | 3,976 (74.89%) | **3,909 (78.31%)** |
| Obstructed original center → clear selected lane | 1,717 | **1,720** |

The new batch's obstruction reduction is **34.46 percentage points**. Across
both V11 batches: 10,301 close requests; 4,448 selected-lane obstructions versus
7,885 original-center obstructions; 3,437 blocked-center-to-clear changes.
Counts per new match are in `batch-03/lane-obstruction-proxy.json`.

There were **11,338 off-center** and **4,525 original-center** eligible normal
updates. All **49,764 normal updates outside the shooting zone** retained the
original center aim. These observations show the selector remains active and
improves its static geometry proxy; the 16-game results show that this proxy
improvement did **not** translate into an established scoring improvement.
Moving opponents, foot behavior, ball height and physical shot completion are
unobserved; no physical-block or causal goal-saving claim is made.

185,346 telemetry ticks parsed, with no dropped records or writer errors.
Two `native_stop_error` events occurred (games 01/06, player 3), both during
`recovering/stop/release_kick`, reporting:
```
RuntimeError('API call failed, code = 400')
```
These are SDK release-call errors, not malformed telemetry or failed launches.
They are not diagnosed as causes of the match outcomes. Raw traces retain them;
the native error count is included in the proxy artifact. No code workaround made.

## Validation and evidence

Command:
```
python3 scripts/check_team_results.py --results match-results/scoring-v11
```
Output:
```
PASS: 16 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 2 animations verified
```
Source/package check:
```
PASS: all 36 team source/config snapshots and package SHA256 identical across V11 batches 02/03 and current main; simulator image and official opponent revision identical; no strategy changes
```

Full output: `rerun-validation.txt`. Tests were not rerun: no code/tests changed;
the established match validator and new real-match run provide this rerun's checks.
`v11-16-game-aggregate.json` retains all totals and warning-type counts.

Time-lapse:
```
/home/ubuntu/repos/booster-studio-s2/match-results/scoring-v11/batch-03/match-01/evidence/match-timelapse.webp
```
Visual check: final CPU-rendered 1–3 snapshot inspected; screenshot is
`snapshot-final.png` beside the animation. Full new-batch artifacts are mirrored
beneath `/home/ubuntu/repos/booster-studio-s2/match-results/scoring-v11/`.
Raw gzip traces, images/animation, packages and signing material remain local-only;
only structured text results/reports/provenance are committed. No PR.

The Booster 3v3 skill is unavailable in this environment. Source unchanged;
checks are basic repository/referee checks, not a full skill-based rules audit.
