# Team v1: built and tested, but not yet competitive

## Bottom line

**Twelve full 600-s matches completed against the untouched official sample**, in
three four-game batches, always alternating our team home/away. Two matches ran
concurrently on the 8-vCPU/31-GiB VM. Four earlier startup failures are separately
retained and are not counted as games or losses. No timer was shortened, no
manual goal/result was injected, and no game was manually ended.

| Candidate | Batch | W/D/L | GF–GA | Mean GD | Our fouls | Our fallen penalties | All warnings / ours |
|---|---|---|---|---:|---:|---:|---|
| Initial | batch-02 | 0/0/4 | 1–28 | −6.75 | 5 | 0 | 0 / 0 |
| First iteration | batch-03 | 1/1/2 | 13–18 | −1.25 | 0 | 0 | 5 / 1 |
| Second iteration; checked in | batch-04 | 1/0/3 | 8–21 | −3.25 | 5 | 5 | 1 / 0 |

**The second iteration regressed scoring and falls.** It eliminated our observed
set-play warnings in its four games, but is not the best-scoring tested variant.
The checked-in `team/` is this latest fully tested candidate, with the larger
restart margin and explicit kick-task reset, not an untested mixture of variants.
The first iteration was better on mean goal difference and had no our-team fall
penalties. Its exact strategy source is retained in
`batch-03/source-snapshot.json` for further work; do not interpret the latest
candidate as a competition-ready improvement. No third iteration was attempted.

The complete per-game table, including side, home–away score, winner, goals
for/against, fouls, warnings and fall penalties, is in [SUMMARY.md](SUMMARY.md).
Each completed match has its original authoritative `result.json` and complete
`events.jsonl`. Per-match/aggregate JSON and CSV summaries are derived from them.
Warnings are whole-match totals; `our_warning_events` attributes a retake to the
offending defending side, **not** the beneficiary in the event's `actor` field.

## Strategy and iterations

The isolated `team/` project preserves the sample's MIT license and unchanged
`src/framework/`. It uses only public `Context` observations in the submitted
agent; the operator/capture scripts are separate and never imported by it.
See [team/STRATEGY.md](../../../team/STRATEGY.md) for details and exact commands.

- Player 1 stays deep at x=−6.6 m, tracks ball y within the posts, and only clears
  in normal play if the ball is in its box and it is the closest eligible
  teammate. On opponent restarts its retreat targets stay inside its box.
- Players 2/3 dynamically select attacker/support with a 0.65 m hysteresis.
  The support outlet is offset and does not chase the same ball target.
- Explicit walking is capped at 1.5 m/s, 1.1 rad/s, with acceleration limits and
  slower turning/near-contact translation. SET/STOP/INITIAL/FINISHED or absent
  referee state issue immediate zero velocity and release kick tasks before
  any recovery logic. Penalized/fallen/missing-pose players do not take roles.

### Initial result and verified failure pattern

The initial near-lateral power-4 restart repeatedly surrendered throw-ins.
For example, `batch-02/match-01/events.jsonl` events 6–10 show our kickoff,
our robot 2's first touch, then an away throw-in at approximately (1.19, −4.45),
with `lastTouchSide=home`. Events 16–19 then show the sample's touch and goal.
The same throw-in pattern recurred after later kickoffs. This is evidence of
lost possession, not proof that it alone explains every conceded goal.

Checks against alternative explanations: our agent logs showed 30-Hz ticks,
all six robot poses, valid changing ball coordinates, successful kick starts,
and referee-confirmed touches. Our initial fouls were four `inactiveRobot`
penalties and one `stopped_motion`, **not** fallen-robot penalties. Thus falls
were not the observed cause of the initial 1–28 aggregate loss. The physical
cause of that stopped-motion penalty was not established; unit tests verify
zero commands, not an instantaneous stop of a robot's physical body.

### First iteration

- Lower restart power to 1.5 and use a forward diagonal whose ray misses both
  goal mouths. Retain the restart origin after referee exclusivity ends;
  only aim goalward once the ball has moved over 0.7 m from that origin.
- Put the keeper's opponent-restart retreat inside its box. Add gentle
  goal-line shuffling when the ball is nearby so it does not freeze in place.
- Increase support offset to 3.3 m and have roamers wait beyond 3.2 m on
  opponent restarts, away from both the mandatory 1.45 m line and the 3 m
  inactivity radius. Keep the two outlets separate during keeper clearances.

This improved the observed aggregate to **13–18**, with zero our-team fouls
and zero our fallen penalties, but one of our goals was disallowed for an
unsatisfied indirect/set-play requirement. The precise SDK/observation/touch
timing behind that incident was not proven. Three retakes in this batch were
awarded to us because the **sample** infringed; they are not our infringements.

### Second iteration

- Increase the restart displacement margin to 1.2 m and release the old kick
  task for one tick before starting a new goalward task.
- Use a shallower initial diagonal, advance the support outlet by 2.6 m,
  restore the sample's 2.0/2.5 m kick engagement range, and use power-5 long
  drives. The explicit walking caps and dedicated keeper remain unchanged.

This yielded **8–21** and five of our `fallenRobot` penalties. Our observed
set-play warnings were zero; the one whole-match warning was the sample's
disallowed indirect goal. Multiple settings changed together, and four games
are too few to isolate which change caused the performance/fall regression.
No claim is made that increasing aggression is safe or that the champion's
formation alone is sufficient to win with this SDK/controller.

## Capture and validation

Final-candidate evidence, all actual CPU EGL/Mesa renders of observed physics:

- `batch-04/match-01/evidence/match-timelapse.webp`
- `batch-04/match-01/evidence/snapshot-start.png`
- `batch-04/match-01/evidence/snapshot-middle.png`
- `batch-04/match-01/evidence/snapshot-final.png`

The animation has **13 frames, 11.7 s playback, 134,754 bytes**. It is a
time-lapse of a complete match, approximately one capture per 45 simulation
seconds, not 11.7 seconds of real-time play. The three PNGs are 960×540; the
final one shows the actual 1–7 final score. `frames.json` records physics times,
referee clocks and captions. Both earlier completed batches also retain their
own animation and three PNGs. Raw intermediate frames stay outside git.

`scripts/check_team_results.py` validated all 12 finals, 600-s durations,
automatic `time_expired` endings, continuous event sequences, final event/score
agreement, authoritative foul totals, source hashes/snapshots and summaries.
It also checked the WebP animation chunk durations/frame counts, size limits,
and three distinct valid PNGs for each capture. All three final-candidate
snapshots were visually inspected. There was no native Studio GPU rendering;
the CPU-rendered evidence is the visual verification.

Pure-Python verification (full output in `unit-tests.txt`):

```text
Ran 47 tests in 0.003s

OK
```

Coverage includes normal/empty/malformed role inputs, fixed keeper, role
hysteresis and unavailability, keeper-box geometry, retreat clearance at
boundaries, restart goal-ray geometry across the field, low-power passes,
phase dispatch with fake SDK handles, SET/STOP bypassing recovery, missing
ball/pose, restart origin persistence/task reset, motion slew/instant zero,
and correct warning/fall-penalty reporting.

Every completed batch includes package SHA-256, source hashes, source snapshots,
prepared-image ID and the official sample revision
`36f0d615af6fd5f7d5475570e27daa3b3ec97632`. Restore a historical strategy by
overlaying its source-snapshot entries on `team/` and rebuilding; the unchanged
framework/utilities and preserved MIT notice are shared by all variants.

## Harness failures and corrected capture issues

1. **Four startup failures, batch-01:** the runner launched before the runtime's
   manager existed: `RuntimeError: booster_agent_manager process not found`.
   No start request was issued. See `batch-01/FAILURE.md` and per-attempt
   `failure.json`. The harness now waits for referee readiness, then both
   teams becoming Active, before starting a match.
2. **One result-fetch race, batch-03/match-01:** immediately after the final
   SSE notification, `/result` briefly returned `{"status":"running","result":null}`.
   That exact premature response is preserved as `premature-result-fetch.json`.
   The actual finalized simulator-written `result.json` was copied from the
   persistent runtime directory and checked against the final event and
   already-observed 2–7 result. The harness now waits for the finalized file,
   rather than trusting immediate API availability. No score/events changed.
3. **Warning attribution:** retake `actor` is the awarded side, not necessarily
   the offender. Derived batch-03 summaries were regenerated from untouched
   events after correcting this; raw referee files were not altered. Unit
   tests cover a named offender and the unnamed opposing-side avoidance case.

Harness logs, referee raw data and intermediate frames remain under
`/home/ubuntu/booster-studio/team-v1-runs/`. Native agent logs remain inside the
stopped containers under `/run/3v3_runner/team_*/data/var/log/booster_agent/`.
Containers are stopped after their games. Parallel isolation was checked: private IPC/cgroup namespaces and the
effective FastDDS profile whitelist (127.0.0.1 and an absent 192.168.127.101
interface) keep agent DDS traffic off the Docker bridge; active container
interfaces were loopback and distinct 172.17.0.x addresses. Peak observed
two-container memory was about 10 GiB, with approximately eight CPU cores busy.

## Remaining limitations

- This team still **loses on average**. The final iteration regressed falls;
  its new release/margin rule safeguard was kept, but not presented as the
  strongest scoring candidate. The earlier tested source remains available.
- The native SDK's persistent kick task walks internally and ignores ordinary
  velocity commands until released. The new caps constrain **explicit walking**,
  not the proprietary internal kick gait. They are not a guarantee against
  contact, sharp internal kick-task turns, falling or residual body motion.
- `fallenRobot` counts are referee penalties after their detection criteria,
  not every fall; continuous physical fall episodes and keeper own-box
  occupancy percentage were not measured. No 97% occupancy claim is made.
- The Booster 3v3 skill is absent from active plugins and its default install
  path. The basic `AGENTS.md`/`NOTES.md` rule checklist and actual referee logs
  were used, not a full official skill audit. Upgrade the development
  environment for that audit before competition submission.
- Both teams' headless native logs repeatedly emitted
  `Service not available after waiting 1s, waiting again...`. The runtime and
  SDK environment were loaded (Active states, 30-Hz ticks and valid observations
  were checked), and games completed, but the optional native service's identity
  was not established. Full Studio UI/service integration is unverified.
- Local testing certificates only; no official certificate acceptance,
  registration or competition submission was attempted. No new `.agent`,
  executable, installer, image archive, certificate or private key is committed.
  The only new binary-format files are the requested PNG/WebP evidence and the
  MIT sample logo required by the copied project.
