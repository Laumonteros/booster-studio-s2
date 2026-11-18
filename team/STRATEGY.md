# Team v1: deep keeper + two roamers

This is a separate MIT-derived agent (`laumonteros_team_v1`), not a modification
of `../sim-3v3-simple-framework`, which remains the benchmark opponent.
The copied platform layer `src/framework/` is unchanged. The upstream MIT
notice remains in `LICENSE`.

## Decisions

- **Player 1** is always the goalkeeper, targeting x = −6.6 m on a 14 m pitch.
  It tracks the observed ball y, clamped 0.3 m inside the posts. It only clears
  in normal play when the ball is inside the actual goal-area rectangle and
  it is no farther from the ball than any other eligible teammate. Otherwise
  it stays deep. On opponent restarts, it retreats within its own box to
  provide the mandatory clearance rather than chasing the ball outside it.
  During open/own-restart play with the ball nearby but another teammate closer,
  it gently shuffles along that line (within the posts) instead of freezing
  beside the ball long enough to be penalized inactive. The initial batch
  actually incurred this penalty; the shuffle does not override SET/STOP.
- **Players 2 and 3** roam. The nearer eligible roamer attacks; the current
  attacker keeps its role until the other is over 0.65 m closer. Losing pose,
  being penalized or recovering removes a player from assignment immediately.
  The support roamer takes a laterally offset second-ball/receiving position,
  ahead and to the side for rebounds rather than crowding the challenger. The keeper never
  silently replaces a missing roamer in midfield.
- The attacker approaches behind the ball with robot avoidance, drives toward
  the opposite side of the opponent goal, and increases kick power within
  4.5 m. This is high-level SDK kicking, not a new low-level gait controller.
- Explicit walking is capped at 1.5 m/s and 1.1 rad/s, with acceleration limits,
  slower translation while turning, and further slowing near observed robots.
  SET, referee STOP, INITIAL, FINISHED and missing referee state issue immediate
  zero velocity and release kicks, bypassing acceleration ramps. Fall recovery
  only runs outside those stationary states. These controls do **not** expose
  or cap the proprietary SDK's internal kick-task gait; reduced falls must be
  judged by match evidence, not assumed from these settings.
- Opponent restarts: retreat radially to a 3.45 m target radius (1.95 m for the
  keeper within its box) when inside the 3.2 m waiting threshold (1.85 m for
  the keeper); stop once
  clear and only rejoin when the referee releases the restart. Near boundaries,
  choose an in-field retreat point.
- Own restarts: lock a roamer as taker. Retain the observed restart origin even
  after the referee's exclusive timer opens. While the observed ball is within
  1.2 m of that origin, target a low-power diagonal progression, **not**
  the goal; after that, release the running kick task for one tick before
  starting a fresh goalward task. This increases the observation/touch margin
  after the first iteration still incurred one disallowed set-play goal.
  Initial testing showed the original
  near-lateral power-4 restart immediately conceding throw-ins. The revised
  target angles avoid both goal mouths geometrically, including wide restarts,
  and use power 1.5 to retain the ball. This uses the legal >0.5 m decisive
  touch route with margin, rather than guessing that a second player touched
  the ball or using a local timer to declare the ball open. At READY, only the
  designated taker can be inside the center circle and all targets are in the
  team's own half. No agent connects to referee HTTP or private physics data.

The support offset was also increased to 3.3 m so a waiting support robot
does not stand inside the referee's 3 m inactivity radius even when its
longitudinal target is clamped near either box. The second iteration advances
the outlet 2.6 m beyond the ball to make the other roamer available for rebounds,
restores the sample's 2.0/2.5 m kick engagement hysteresis and power-5 long drive,
and uses a shallower initial diagonal to reduce turning. Explicit walking
speed/acceleration caps and the dedicated keeper are unchanged.

The champion analysis motivated this formation and focus on falls. It does
not establish that copying the formation will beat either the sample or the
champion. A deep stationary keeper can itself incur inactivity penalties when
the ball remains nearby; the benchmark reports actual penalties rather than
claiming foul-free compliance. Support positioning is not a proven passing
combination; it is a receiving/rebound option with dynamic closest-ball swaps.

## Reproduce

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
docker start agent-dev-6b31c279425950a824c2fc8e8397389f
bash scripts/build_team.sh agent-dev-6b31c279425950a824c2fc8e8397389f \
  "$HOME/booster-studio/team-v1-new.agent"
python3 scripts/run_team_batch.py \
  --package "$HOME/booster-studio/team-v1-new.agent" \
  --batch unique-batch-name --workers 2
```

Initialize the official Studio runtime/prepared image first as in `../NOTES.md`.
Use the actual initialized agent-dev container name on a new installation.
Build certificates are ephemeral, local-only and deleted by the helper; no
event signing or submission acceptance is implied. Package output must not
already exist. Credentials and compiled `.agent` packages are never tracked.

The operator harness uses Docker cgroup/IPC isolation and localhost-only
referee ports, waits for simulator readiness and both agents becoming Active,
then starts the unshortened 600-s match. Four matches alternate home/away.
`--workers 2` runs two concurrently, not four: the VM has 8 vCPUs/31 GiB RAM.
Runtime logs and large raw data go to `~/booster-studio/team-v1-runs/`; selected
results/events and images go to `match-results/team-v1/<batch>/`. Each run uses
new containers/directories and will not overwrite prior failed or completed
matches. A package hash, source hashes and sample revision are recorded.

The first match in a batch captures actual physics about once per 45 simulation
seconds into a **time-lapse**, not real-time video. It is encoded as a looping
WebP with 0.9 s per frame (≤30 s, ≤10 MiB), alongside start/middle/final PNGs and
frame timestamps. Read-only capture code runs outside either strategy. The
score is the authoritative referee score; `fallenRobot` counts are referee
**fall penalties**, not every physical falling episode. Four unseeded matches
are a smoke benchmark, not a statistically reliable league ranking.

## Results

See `../match-results/team-v1/REPORT.md` for every attempted batch, exact outcomes,
infrastructure errors, any strategy iteration and evidence paths.
