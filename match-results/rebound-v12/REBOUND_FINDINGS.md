# V12 rebound/second-ball evidence before benchmarking

Inputs: both V9 batches (16 games) and both V11 batches (16 games). No pilot
matches included. V11 reference: 8W/3D/5L, 37–29, +0.50 mean GD.

## What can actually be measured

In V11, all **1,114 consecutive recorded ball-touch event pairs** changed sides.
This is not a reliable basis for counting arbitrary same-team second touches or
completed physical shots. We therefore use **pose/proximity flight windows**,
not event-delimited controlled possessions or a claim of physical rebounds.

`scripts/analyze_rebounds.py` identifies a normal-play attacking field player
within 0.65 m of the ball with a native kick request, followed within 0.5 wall
seconds by a loose observation where **every observed robot is over 0.9 m away**.
Ball observations must be fresh (under 0.15 wall seconds old). A second trigger
handles a goal-zone request followed within three seconds by opponent proximity
and then a loose flight: an **opponent-deflection proxy**, not a confirmed save.

The next observed robot within **0.65 m** wins the proximity race. Recoveries
within 0.15 m of another robot's distance are ambiguous and excluded. Flights
over two wall seconds or 3 m of displacement, missing/stale observations, and
stoppages are censored. The original supporting robot's identity is retained
through subsequent role changes. Long clears and unobserved flights are not
silently counted as lost rebounds.

## Measured baseline

| Window proxy | V9: 16 games | V11: 16 games | Combined |
|---|---:|---:|---:|
| Resolved loose flights | 192 | 193 | **385** |
| After close own native request | 185 | 186 | **371** |
| After opponent-proximity deflection | 7 | 7 | **14** |
| Next proximity: opponent | 155 | 159 | **314** |
| Next proximity: original support | 28 | 19 | **47** |
| Next proximity: other own robot | 9 | 15 | **24** |

There were 189 attacking-half windows and 88 following goal-zone requests
(ball within 4.5 m of goal). **702** flights were censored and **5** recoveries
ambiguous. Results are conditional on this observable, short-flight cohort.

At the first loose observation:
- Support → ball: median **2.529 m**.
- Support → eventual recovery point: median **3.557 m**.
- Nearest opponent → that point: median **0.612 m**.
- An idealized close flank spot → that point: median **1.979 m**.

This is **not simply support standing too far from the ball**: support was
typically about 2.5 m away, but poorly placed for the subsequent ball path.
Opponents were already substantially closer to the eventual recovery point in
**317/385** windows (0.3 m margin); support had that margin in **51/385**.
Moving support cannot retroactively win most of these races.

## Could a closer flank have arrived first?

The idealized station is 1.25 m laterally off the ball-to-goal axis, on the
supporter's current side. It trails 0.8 m in our half, blending continuously
to 1.5 m goalward by ball x=2. Positions remain 0.75 m inside field boundaries.
This is **already-prepositioned** geometry, not an instantaneous feasible move.

For the strongest static endpoint test, only **2/314 opponent-won windows**
would flip to a 0.3 m distance lead if support were already at that station.
This disproves a large pool of easy endpoint pickups in the observed cohort.

An alternative model checks interception along the recorded flight before the
opponent reaches its endpoint. All robots get the same straight-line speed and
0.65 m capture radius; first reach must lead by 0.1 wall seconds. At nominal
0.75 / 1.0 / 1.5 m per wall second, **9 / 10 / 14** opponent-won windows become
modeled flank interceptions. V11 alone contributes **2 / 3 / 5** of those.

**Important counterevidence:** the idealized station also gives up modeled
existing pickups. At 1.0 m per wall second, actual support leads in **51**
windows versus **21** at the fixed flank. Consequently these models do **not**
predict a net improvement or justify promotion. They omit headings, locomotion
latency, obstacles, body/foot contact and changes to the future ball path. Wall
time is not calibrated robot travel time. They demonstrate a limited potential
interception opportunity and substantial positional trade-offs, not guaranteed
recoveries. The requested full 16-game experiment is necessary.

`baseline-rebound-audit.json` retains all per-match counts, recovery points,
starting support poses, counterfactual station positions and sampled paths.
Reproduce with:
```
python3 scripts/analyze_rebounds.py /path/to/set-plays-v9 /path/to/scoring-v11 --output baseline-rebound-audit.json
```

## The one frozen V12 experiment

Only normal support dispatch changes. `rebound_support.py` and isolated
`rebound_params.py` implement:
- A close attacking flank, smoothly blending from a defensive trailing station.
- Persistent side choice, clearance from the selected V11 shot ray and attacker,
  and a trailing/wider fallback when clipping would obstruct the lane.
- A slow 0.4 m, eight-second longitudinal patrol near the station. Nearby motion
  uses at most 0.35 m planner steps (at most 0.525 m/s requested translation),
  no commanded yaw, and existing ball/robot/goal obstacle avoidance. Far approaches
  retain existing path planning rather than imposing a global attacker slowdown.
- A **pose-progress**, not command-activity, inactivity guard. If within 3 m of
  the ball without 0.25 m displacement for three seconds, temporarily target an
  outward escape. Resume close support after 0.8 m physical progress or clearing
  the inactivity radius. Gaps in actionable observations reset the budget so SET,
  recovery and pauses are not charged as normal-play waiting time.

This guard cannot guarantee physical movement through arbitrary blockage; the
benchmark's actual inactivity/fallen penalties, not nonzero commands alone, judge
safety. No source changes are made between the two benchmark batches.

Keeper, attacker selection, attacking/shooting primitives, native task ownership,
kick power, framework, throw-in handoff and opponent-restart exit are unchanged.
All our restart support remains the old support behavior. No v10 cap carried over.
