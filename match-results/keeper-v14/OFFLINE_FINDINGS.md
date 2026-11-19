# V14 keeper options: fixed-trajectory estimates

Input: all 57 rows of V13's `GOALS.csv`, checked against the trajectory audit by
match, regulation time and classification. The CSV is retained here unchanged;
input SHA256 values and all per-goal model gaps are in `offline-estimates.json`.
The trajectory audit is retained on `devin/defense-v13` at
`match-results/defense-v13/baseline-conceded-audit.json`.

## A. Bisector positioning

The anchor is the intersection of the keeper's depth line with the sum of the
unit vectors from the ball to the two goalposts. Keep the existing post margin,
side-to-side anti-inactivity shuffle and incoming-ball projection. Retreat
smoothly to remain 0.3 m behind a close ball, down to the existing 0.15 m backstop.
Only normal play changes; restart/READY/STOP behavior is unchanged.

Replay starts at the first recorded keeper pose in each goal's 12-wall-second
lead-in. It holds only previously observed ball/velocity inputs during 0.05 s
substeps, limits translational speed, and interpolates the final ball crossing of
the moving keeper plane. Non-normal play, recorded clearing and unavailable
periods retain the recorded keeper poses. Both V11 and the proposed controller
use the same simplified motion model. Coverage means a gap no larger than 0.45 m;
it does **not** mean a physical save.

Among 2,109 active keeper intervals with accepted requests above 0.2 m/s,
observed translational speed had median 0.1555 m/wall-s and IQR 0.0824–0.2560.
The sweep includes slower/faster sensitivity settings. Maximum depths of
0.4/0.6/0.8/1.0/1.2 m were compared; a distant ball keeps the 0.4 m home line.

| Speed bound (m/wall-s) | Modeled V11 covered | 0.4 m bisector covered | Gains / losses vs modeled V11 | Net |
|---:|---:|---:|---:|---:|
| 0.05 | 23 | 25 | 5 / 3 | +2 |
| 0.10 | 28 | 37 | 10 / 1 | +9 |
| 0.15 | 35 | 42 | 8 / 1 | +7 |
| 0.20 | 35 | 39 | 6 / 2 | +4 |
| 0.25 | 39 | 44 | 6 / 1 | +5 |
| 0.50 | 49 | 49 | 1 / 1 | 0 |

At the median-speed setting, 21/30 recorded lateral misses are covered. Five
recorded close crossings lose coverage; the apparent +18 against actual poses is
**not** the estimate used to choose the intervention. The same model already
covers 35 baseline goals versus 24 actual close crossings, demonstrating its
optimism. The like-for-like estimate is **+7 crossings** at median response,
**+4 to +9** across the measured response range, and **0 to +9** over the full
sensitivity sweep. These are in-sample geometry estimates, not goals prevented.

Advancing farther was less robust. At median response, net gains for maximum
depths 0.4/0.6/0.8/1.0/1.2 m were +7/+5/+2/0/0; several deeper settings lost net
coverage at other speed bounds. Therefore retain the 0.4 m maximum depth and
change the angle anchor plus close-ball depth adjustment, rather than advancing
the keeper farther out.

## B. Clearance targeting

All 19 recorded opponent recoveries after keeper contacts occur inside their
retained lead-in windows (0.36–4.92 wall-s before the goal). Only four have a
`keeper:clear` request before recovery in those windows. Fifteen have no such
request; the contact flag alone must not be treated as a deliberate clearance.

For the four observed attempts, trace the recorded ball path up to recovery,
convert the native body direction to a field direction, and compare its first
3 m ray against hypothetical outlets at (-3, -4) and (-3, +4). Outlet requests
are computed from the keeper pose, as the actual attack API does. A ray is
geometrically obstructed if an observed opponent is within 0.45 m of its segment.

| Source / goal time | Maximum forward ball travel before recovery | Requested-ray opponent gap | Best wide-outlet gap | Changes obstructed → clear? |
|---|---:|---:|---:|---|
| V9 b01/m01, 276.474 s | 0.723 m | 0.072 m | 1.604 m | yes |
| V9 b01/m01, 563.398 s | <0.001 m | 0.178 m | 0.618 m | yes |
| V9 b01/m08, 259.088 s | 0.085 m | 1.333 m | 2.932 m | no: already clear |
| V11 b02/m01, 331.528 s | 0.100 m | 1.159 m | 3.388 m | no: already clear |

Requests aimed approximately forward toward the opponent goal; they did not
produce long clearances in these four windows. Two replacement rays avoid a
static opponent corridor, but only one of those attempts shows substantial
forward ball movement. The other request is not evidence that a kick completed.
Estimate: **at most two outlet-lane opportunities among 57 conceded goals**,
only one with a visible forward release. This is not a claim of two prevented
goals: execution, moving opponents, ball friction and subsequent play are not
simulated. Per-attempt requested angles and observed paths are retained in JSON.

## Decision and limitations

Implement A only: its +4 to +9 like-for-like coverage estimate over the measured
motion range is larger than B's two-opportunity ceiling. Do not combine speculative
effects: changing position also changes clearance eligibility and later contacts,
so joint independence is not established. Keep clearance target, eligibility and
native task behavior unchanged.

The model cannot reproduce robot bodies, falls, acceleration, yaw, collisions,
native kicking or changed ball trajectories after hypothetical contact. It uses
decimated telemetry, holds observed clearing/restart histories fixed, and is not
a calibrated simulator. In particular, an unchanged recorded goal path after a
hypothetical interception is physically inconsistent. The 16-game frozen
benchmark, not these optimistic coverage proxies, decides whether V14 improves.

Reproduce:

```sh
python3 scripts/estimate_keeper_options.py \
  --goals match-results/keeper-v14/GOALS.csv \
  --audit /home/ubuntu/repos/booster-studio-s2/match-results/defense-v13/baseline-conceded-audit.json \
  --output match-results/keeper-v14/offline-estimates.json
```
