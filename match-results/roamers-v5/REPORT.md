# Candidate v5 — rejected, not pushed

Base: telemetry commit `043e204`, itself from main `e2db7d9` (PR #4 keeper).
Implementation remains locally in `/home/ubuntu/repos/booster-studio-s2-roamers-v5`
on `devin/roamers-v5`, uncommitted. The telemetry branch's live `team/` contains
**only main plus opt-in logging**, not the failed policy. The benchmark source
snapshot is an archive, not an active/promoted team.

## Targeted changes

- `team/src/roamer_tactics.py`, `roamer_params.py`: opponent-lane-aware choice
  among goal openings, stable target hysteresis, blocked-lane short dribble,
  and correction for the native goal's robot-centred 8 m projection.
- Roamer-only immediate 2 m restart escape before routing to the baseline
  >3.2 m inactivity-safe waiting point; do not cut within the legal radius.
- `team/src/main.py`: dispatch those target choices only for roamers and keep
  per-roamer target memory. Existing interfaces are unchanged; the store addition
  is backward-compatible. Own restricted restarts retain main's existing logic.
- `tests/test_roamer_v5.py`: empty/invalid observations, blocked/open lanes,
  full native projection geometry, observed endline escape and safe wait routing.

Keeper command body is AST-identical; existing Player methods, shared/keeper
parameters, keeper helpers, framework and sample are byte-identical. Baseline
approach algorithm/thresholds and native session ownership are preserved, although
the newly selected/compensated target also changes its derived approach direction.
Support was deliberately unchanged to avoid another broad controller rewrite.

## Full matches

Two at a time; four home/four away; all ended naturally at 600 regulation seconds
with `endReason=time_expired`. No failed launches. Scores are ours–sample;
fouls/falls/warnings below are **our team**, not whole-match warning totals.

| Match | Side | Score | Fouls | Fallen penalties | Warnings |
|---|---|---:|---:|---:|---:|
| 01 | Home | 1–2 | 1 | 1 | 0 |
| 02 | Away | 3–5 | 0 | 0 | 0 |
| 03 | Home | 1–6 | 0 | 0 | 0 |
| 04 | Away | 0–2 | 1 | 0 | 1 |
| 05 | Home | 1–4 | 2 | 0 | 1 |
| 06 | Away | 2–4 | 1 | 1 | 0 |
| 07 | Home | 2–3 | 0 | 0 | 0 |
| 08 | Away | 1–4 | 1 | 0 | 1 |
| **Total** | | **11–30** | **6** | **2** | **3** |

**0W/0D/8L, mean GD −2.375.** Baseline −2.0/zero wins; required ≥−0.5,
more wins, zero own falls/warnings. Every acceptance condition fails. No second
batch: not a thin positive margin. Candidate branch was not pushed.

Rule events:
- Match 01, 264.830 s: keeper/player 1 `fallenRobot`. Keeper source was untouched;
  the causal mechanism is unverified. It still counts against our team gate.
- Match 04, 234.766 s: player 2 `defender_set_play_interference` at a goal kick,
  penalty plus retake. The new escape logic is not sufficient to guarantee safety.
- Match 05, 152.356/296.152 s: player 3 `illegalPosition`; 557.716 s:
  our `goal_disallowed_indirect`. The unchanged own-restart path remains unsafe.
- Match 06, 558.738 s: player 3 `fallenRobot`.
- Match 08, 525.860/525.880 s: player 3 goal-kick interference, penalty/retake.

The data do not justify calling the changes an improvement or attributing every
failure to a single cause. There was no ablation or second candidate in this step.

## Checks / evidence

```
Ran 86 tests in 0.012s

OK
```
```
[0003.2s INFO] Agent package sign succeed
[0003.2s STEP] Build completed: laumonteros_team_v1-1.0.0.agent
```
```
PASS: 8 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 1 animations verified
```

Local-only evidence (binary formats deliberately not committed):
- `batch-01/match-01/evidence/match-timelapse.webp`
- `batch-01/match-01/evidence/snapshot-final.png`

The final 960×540 CPU-rendered snapshot was visually inspected: finished, 0.0 s,
home 1–2 sample. This is match evidence, not proof of improved tactics.
The validator checks animation length/size/frame provenance; no real-time video
claim is made. Raw per-match telemetry is `batch-01/match-XX/telemetry.jsonl.gz`.
Unlike the baseline analysis pair, this package was built with the flag **off**
and logging successfully enabled solely by `--telemetry`/container environment.
