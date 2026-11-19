# V13: all 57 V9/V11 goals against

Sources: V9 batches 01/02 (28 goals against), V11 batches 02/03 (29),
32 completed matches. `GOALS.csv` has one row per conceded goal, including
turnover position, release-proximity position/range/angle, all three own poses
at that observation, keeper pose at the crossing, action/coverage classification,
own-contact flags and binding-limiter evidence. `baseline-conceded-audit.json`
retains the associated events, snapshots, trajectories and decision replay.

## Ranked observable keeper failure groups

| Rank | Group | Goals |
|---|---|---:|
| 1 | Ball crossed the keeper's moving x-plane >0.45 m from its y-position | 30 |
| 2 | Ball crossed that plane within 0.45 m of the keeper | 24 |
| 3= | Keeper recovering/unavailable at crossing | 1 |
| 3= | Keeper behind the goal line/out of goal position | 1 |
| 3= | No fresh, contiguous observed keeper-plane crossing | 1 |
| | Total | 57 |

These are mutually exclusive observational failure groups, **not 57 proven
physical root causes**. The 0.45 m band is an analysis convention, not a verified
robot save radius. A close crossing does not establish a save attempt, contact,
or a ball passing through the legs. The crossing is the last observed crossing
before the goal; in 18 cases the final opponent-proximity observation follows
that crossing, i.e. the opponent finishes after passing the keeper's line.

The unavailable case is V9/01/07 at 168.726 s: keeper action `recovering`,
with rejected movement commands. The out-of-position case is V11/03/02 at
354.446 s: final keeper x=-7.242 m, behind the own goal line. V9/01/05 at
119.034 s lacks a sufficiently contiguous crossing; it is not silently assigned
to a positioning cause. No advanced-after-clearing category was observed.

## Attack lead-ins (separate, overlapping causal dimensions)

| Last recorded attack lead-in | Goals |
|---|---:|
| Opponent recovery after a recorded keeper contact | 19 |
| Own turnover in defensive third (x<-3 m) | 18 |
| Touch recorded during a restart | 9 |
| Own turnover in middle third (-3<=x<3 m) | 8 |
| Restart without a recorded later turnover | 2 |
| Own turnover in attacking third (x>=3 m) | 1 |
| Total | 57 |

The keeper-contact flag uses the authoritative opponent-touch event's
`previousTouchRobotKey`, not mere proximity. It does **not** prove the preceding
contact was a save/rebound rather than a clearance or incidental touch. Two of
the 19 have `keeper:clear` within four wall seconds of the goal, both in
V9/01/01 (276.474 and 563.398 s). Neither establishes an early-commitment goal:
the keeper was no longer advanced at the decisive crossing. The other 17 have
no such recent clearing action; rebound versus incidental contact remains
unverified. Full prior reset events and turnover snapshots are retained for
each goal rather than inferring the original start of a long attack from one
late keeper recovery.

## Shot/release geometry and own contacts

There is no public physical-shot event or opponent kick-command trace here.
The reported origin is the **last fresh ball observation within 0.65 m of any
opponent during the 12 wall seconds before the goal**. All 57 have such an
observation. It may describe a dribble, late finish, rebound or ball already
released from a foot; it must not be called the actual shot location. Range
is distance from that ball point to (-7,0); angle is its absolute bearing
relative to the goal-centre axis. All coordinates are our team-relative frame.

| Release-proximity range | Goals |
|---|---:|
| <=2 m | 35 |
| >2 to <=4.5 m | 16 |
| >4.5 m | 6 |

Median range: **1.565 m**. Angles: <=20 degrees **12**; >20 to <=45 degrees
**6**; >45 degrees **39**. These are finishing-observation proxies, not an
independent count of physical shots from those distances or angles.

For **33/57**, the last emitted contact side before the goal is ours. The
last emitted own actors are keeper 21, roamer 2 five, roamer 3 seven. The
event stream coalesces same-side contacts: a later opponent event can name a
different `previousTouchRobotKey` from the earlier emitted own actor. Therefore
the exact final own robot, contact time and deflection-versus-miskick cannot
always be recovered. These 33 are **own-final-contact-side goals**, not 33
confirmed involuntary deflections. The other 24 have no recorded subsequent
own-side contact after the last opponent touch. The CSV and JSON expose the
observations instead of inventing contact classifications.

## Selected actionable mechanism inside the largest failure group

In **12 of the 30 lateral misses**, at least one incoming-intercept request
within two wall seconds before crossing is saturated at the nearby-robot speed
limit. In **11**, that saturation occurs while the requested target y is
within 0.30 m of the eventual crossing y. Requests exceed the contact cap,
and the accepted chassis speed matches that cap within 2%. No interpolation
or hypothetical movement is counted as an accepted command.

Reachability chain:

1. Every retained batch's `main.py`, `tactics.py` and `param.py` hashes match
   the audited code. Across **752,972 ticks**, replaying phase selection,
   velocity filtering, keeper tracking and waypoint generation reproduces
   **all 477,422 recorded keeper waypoints exactly**.
2. Actual `keeper:intercept` actions take the fixed keeper branch in
   `main.py`, which calls the keeper `Player.walk_to` with `face=0`.
   `roster.py` uses `player.Player` only for robot 1; field robots use the
   separate `field_player.Player`.
3. `walk_to` requests omnidirectional motion for these <=0.8 m waypoints.
   `player.Player.set_velocity` halves the turn-adjusted 1.5 m/s limit when
   any other robot is within 0.85 m. Public pose snapshots show that proximity.
4. Logged accepted requests in the 11 cases equal the resulting cap, typically
   0.70–0.75 m/s, while their target requests are larger. The keeper then
   remains outside the 0.45 m crossing band.

**Verified:** this controller limits those movement requests despite a correct
intercept target. **Unverified counterfactual:** removing the limit would move
the physical robot far enough in time to prevent any particular goal. Native
gait/contact dynamics and exact physical shot timing are not observed.

### Attempt to disprove the hypothesis

The cap is not sufficient to cause a goal: of **499** saturated incoming
intercept samples across the corpus, **264** are outside four-wall-second
windows around any conceded goal. Two of the close-coverage goals also contain
correct-target capped samples. Conversely, 19 of the 30 lateral misses do not
have a verified correct-target binding-cap sample. The change does not claim
to explain all 30, or to fix the 24 close-coverage goals.

The largest measured failure group is lateral coverage failure. The chosen
single intervention addresses its demonstrated controller-level restriction;
it is deliberately narrower than an unproven keeper-position rewrite,
new clearing policy, or roamer recovery overhaul. The complete 16-match
benchmark, not the geometric proxy, decides whether that intervention helps.

## Frozen V13 change

Only `team/src/player.py` changes at runtime: robot 1 with action
`keeper:intercept` does not receive the nearby-robot 0.5 multiplier. The
existing maximum speed, turn-related speed reduction, acceleration limits,
stop semantics and missing-state handling remain. Tracking/patrol, clearing,
READY, restarts, recovery filtering, field-player code and scoring are unchanged.

Seven motion tests cover interception, preserved protected actions, non-keeper
exclusion, global/yaw/acceleration limits, immediate stop, missing observations
and the recorded V11/03/02 capped interception. Four analyzer tests cover
crossing interpolation, gaps/missing observations, past-only lookup and
accepted saturated-command evidence.
