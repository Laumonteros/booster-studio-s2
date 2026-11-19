# V9 scoring-chance audit: both unchanged batches

Inputs: `set-plays-v9/batch-{01,02}/match-*/{events.jsonl,telemetry.jsonl.gz}`.
Batch 02 is archived on `devin/v9-rerun` at
`92c3cf2a1a0316acc946661c3dbddad8d5039518`. Both batches have byte-identical
team-source provenance, based on main `ff2de4b`.

## Definitions and corrections

These are **last-touch episodes and command/geometry proxies**, not authoritative
controlled possessions, completed physical kicks, saved shots or collision data.
An episode begins with an own-team referee touch and ends at an opponent touch,
placement, goal or finish. A goal immediately following that opponent touch,
before any further touch/placement, is credited back as a deflection outcome.
This credits 12 goals that a strict last-touch cutoff would wrongly call losses.
No elapsed-time heuristic is used for that attribution.

Only public normal PLAYING/NONE/ball-free observations are analyzed. An in-range
episode has the ball within **4.5 m of the physical goal center (7,0)**. A close
request additionally has an attacking roamer within **0.8 m of the ball** issuing
a native kick update. Commands are not counted as individual physical shots.

The sample aims at **(7.25,0)**, 0.25 m behind the line. Its requested direction
is projected onto the physical goal plane before testing clearance. A lane is
called blocked when an observed opponent center lies within **0.45 m** of that
segment. Alternatives are physical goal-mouth points **(7,−1)** and **(7,+1)**,
0.3 m inside the posts. This is a static geometric model, not proof of a save.

Initial exploratory counts used a strict touch cutoff and idealized center-line
aim. **The final counts below supersede those preliminary numbers.** The final
analyzer and regression tests include deflection credit and the actual baseline
aim depth.

## Chance outcomes, one category per in-range episode

| Outcome | Batch 01 | Batch 02 | Combined |
|---|---:|---:|---:|
| Scored, including immediate deflection continuation | 19 | 16 | **35** |
| Non-scoring; every close request's center lane blocked | 30 | 50 | **80** |
| Non-scoring; no close in-range native request | 29 | 27 | **56** |
| Non-scoring; at least one clear center request | 14 | 15 | **29** |
| **Total in-range episodes** | **92** | **108** | **200** |

There were **626** total last-touch episodes and **136** in-range episodes with
close requests. Two of the 37 match goals fall outside this normal-play cohort;
these categories are not intended as a decomposition of all match goals.

The largest measured non-scoring category is **blocked center-only requests**:
80/200 in-range episodes. In **54/80**, at least one off-center candidate was
geometrically clear at a close-request sample: **22/30** in batch 01 and
**32/50** in batch 02. This is the single policy issue selected for V11.

At tick level, **4,165/5,277** close-request samples had an obstructed actual
center ray; **1,667** of those had a clear off-center candidate. Tick counts
overweight long contests, so episode counts drive the ranking.

## Other proposed losses

- **Possessions lost before shooting:** 56 in-range last-touch episodes had no
  close in-range request before ending without a credited goal. This does not
  prove a robot had controlled possession or could have shot earlier.
- **Too-far shots:** 494/626 episodes included close-ball native updates outside
  the 4.5 m shooting range. They cannot be labeled 494 wasted shots: the SDK's
  persistent task also chases, dribbles and clears. There is no trustworthy
  physical shot counter in these logs, so no range/power change was justified.
- **Support/rebounds/passes:** in 48/115 opponent-recovery endings with a fresh
  (under 0.2 wall seconds old) in-range support observation, support was more
  than 2.5 m from the ball. This is a secondary availability proxy, overlaps the
  categories above, and does not prove a missed rebound/pass. Support is unchanged.

## Reachability, falsification and uncertainty

The verified policy chain is:
`field_logic._act_normal → attacker.action='attack' → attack → plan_kick`, which
unconditionally selected `opponent_goal(context)` on V9. The resulting backend
directions were checked, not merely inferred from source: **all 9,137** close,
in-range normal attacking updates across both full traces match the direction
toward (7.25,0) within 1e−6 radians (maximum error 8.88e−16). This wider direction
check includes samples outside our last-touch episodes.

To challenge the lane-loss explanation, scored episodes were checked too:
**12 scored despite all their observed close center requests being geometrically
blocked**. Thus the blocked-lane model is not a physical block detector, and
80 must not be read as 80 shots saved or 80 recoverable goals. Goalkeeper motion,
ball height, native foot placement and deflections remain unobserved.

What is established is a policy omission: the default normal attacker does not
use available goal-mouth alternatives. Whether choosing them improves scoring
must be answered by the new matches, not the counterfactual geometry alone.

Replay of the final selector over V9 would choose an off-center aim in
**19,187/144,847 normal native updates** (13.25%). In the wider 9,137 close-request
set, **2,953** baseline-blocked requests become geometrically clear. These are
counterfactual requests, not predicted goals or independent opportunities.

## Reproduction and scope

```
python3 scripts/analyze_scoring.py /path/to/set-plays-v9 --output v9-chance-audit.json
```

`v9-chance-audit.json` retains per-match counts and bounded episode samples;
`direction-and-replay.json` retains the independent direction/replay totals.
The diagnostic script is operator-only and never imported by strategy code.

V11 changes only normal attacking aim selection within 4.5 m of goal. Clear
center aim retains the exact original (7.25,0) target; side candidates lie inside
the physical goal mouth. Hysteresis retains a clear chosen lane and requires a
meaningful improvement before switching between obstructed lanes. Native task
ownership, power, kick/approach thresholds, walking, support, keeper, throw-in
handoff, opponent exit and all restart commands are unchanged.

An initial two-game pilot was cancelled before any completed regulation result
after the direction check exposed the aim-depth detail. Its incomplete artifacts
and source are retained under `/home/ubuntu/booster-studio/v11-pilot-goal-depth/`.
The corrected source was rebuilt and the final eight matches use **batch-02**;
pilot runs are excluded from validation and reported performance.
