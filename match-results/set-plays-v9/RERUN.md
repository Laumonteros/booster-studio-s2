# V9 unchanged rerun and 16-game baseline

Branch `devin/v9-rerun` from `origin/main` at
`ff2de4b7afd02b5a754333164131d4048956b634`. No source/config changes.
The batch-01 and batch-02 `team_source_sha256` mappings are identical.
Eight new full 600-second regulation matches, alternating home/away, telemetry
enabled, two concurrent workers; zero failed launches.

Scores are ours–sample. Counts are our team's referee penalties/warnings.

| Game | Side | Score | Falls | Warnings |
|---|---|---:|---:|---:|
| 01 | Home | 1–0 | 0 | 0 |
| 02 | Away | 3–2 | 1 | 0 |
| 03 | Home | 2–1 | 0 | 0 |
| 04 | Away | 1–2 | 0 | 1 |
| 05 | Home | 1–2 | 0 | 0 |
| 06 | Away | 2–3 | 0 | 0 |
| 07 | Home | 4–0 | 0 | 0 |
| 08 | Away | 2–2 | 0 | 0 |

| Batch | W/D/L | GF–GA | Mean GD | Falls | Own warnings |
|---|---|---|---:|---:|---:|
| 01 | 4/2/2 | 21–16 | +0.6250 | 2 | 1 |
| 02 | 4/1/3 | 16–12 | +0.5000 | 1 | 1 |
| **Combined** | **8/3/5** | **37–28** | **+0.5625** | **3** | **2** |

Combined warning types: one `set_play_retake:free_kick_avoidance_radius`
(batch 01), one `goal_disallowed_indirect:indirect_goal_requirement_not_satisfied`
(batch 02). All other own warning types zero. These are event counts, not a
claim that all physical falls or positioning penalties were absent.

Validation command:
`python3 scripts/check_team_results.py --results match-results/set-plays-v9`

```
PASS: 16 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 2 animations verified
```

See `rerun-validation.txt`, `v9-16-game-aggregate.json` and `batch-02/`.
Time-lapse: `batch-02/match-01/evidence/match-timelapse.webp`;
snapshot: `batch-02/match-01/evidence/snapshot-final.png`.
Raw telemetry, visual binaries, packages and signing material remain local-only.
Pushed as requested, no PR.
