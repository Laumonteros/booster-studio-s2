# v14-pred (ball-trajectory prediction for roamers) vs v14 — 16 matches vs official sample

Code: commit 3e18912 (package sha256 05c228a5…, used for both batches).

| | v14 | v14-pred |
|---|---|---|
| W/D/L | 8/7/1 | 12/1/3 |
| GF–GA | 37–22 | 43–26 |
| Mean GD | +0.94 | +1.06 |
| Our fallen-robot penalties | 2 | 0 |
| Our penalties (total) | 5 (2 fallenRobot, 3 inactiveRobot) | 6 (5 inactiveRobot, 1 illegalPosition) |
| Opponent penalties | 14 | 8 |

Per-match GD v14-pred: batch-02/match-01 (replacement, home) +2; batch-01 matches 02–16: +2 +1 −3 +1 0 −2 +2 +3 +2 +4 +1 +1 −3 +3 +3.
batch-01/match-01 failed before kickoff (sample team never activated; see failure.json) and was replaced by batch-02/match-01, which also has the time-lapse in evidence/.
"Falls" = 10 s fallen-robot penalties from referee events, not every physical fall. Mean-GD gap (+0.12) is within batch-to-batch noise.

## Confirmation batch (batch-03, same package sha256 05c228a5…, 16/16 finished)

| | v14 | v14-pred first | v14-pred confirmation | v14-pred pooled (32) |
|---|---|---|---|---|
| W/D/L | 8/7/1 | 12/1/3 | 9/3/4 | 21/4/7 |
| GF–GA | 37–22 | 43–26 | 32–24 | 75–50 |
| Mean GD | +0.94 | +1.06 | +0.50 | +0.78 |
| Our fallen-robot penalties | 2 | 0 | 4 | 4 |
| Our inactive-robot penalties | 3 | 5 | 1 | 6 |
| Our penalties (total) | 5 | 6 | 11 (4 fallen, 4 illegalPosition, 2 motionInSet, 1 inactive) | 17 |

The first batch's lead over v14 did not repeat: the confirmation batch has a lower mean GD than v14, and pooled v14-pred (+0.78) is slightly below v14 (+0.94). Wins are still more frequent (21 of 32 vs 8 of 16) because v14 draws more. Identical code gave 0 and then 4 fallen-robot penalties, so fall counts in a single 16-match batch are noisy.
