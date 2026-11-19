# V14: keeper geometry

Branch `devin/keeper-v14`, based on V11 `6c2c637`. No PR.

**Measured improvement:** 8/7/1, 37–22, mean GD **+0.9375**, versus V11's
8/3/5, 37–29, **+0.5000**. The +0.4375/game gain is entirely fewer concessions;
scoring is unchanged. This is a better 16-game result, not proof of a dominant
team or statistical certainty. Fallen penalties increased from one to two.

## Offline decision

All 57 `GOALS.csv` rows were checked against V13's trajectory audit.

- **Positioning:** true ball-to-posts angle-bisector anchor, with a smooth retreat
  behind close balls. Compared maximum depths of 0.4/0.6/0.8/1.0/1.2 m. Retaining
  the 0.4 m maximum was most robust. At the median observed motion setting, the
  proposed controller covered **21/30 lateral misses**. In a like-for-like
  kinematic replay it gained **8 crossings and lost 1: net +7**, versus modeled
  V11; net +4 to +9 across the measured response range, 0 to +9 over the full
  sensitivity sweep. The model overpredicts baseline coverage (35 versus 24
  observed), so these are optimistic geometry estimates, **not saves or goals
  prevented**.
- **Clearances:** the 19 keeper-contact recoveries are not 19 deliberate
  clearances. Four have clearing requests in their recorded lead-ins. Their
  maximum forward ball travel before recovery was **0.723/<0.001/0.085/0.100 m**.
  Two hypothetical wide outlet rays remove a static opponent obstruction, but
  only one of these attempts shows substantial forward ball travel. Estimate:
  **at most two outlet-lane opportunities**, not two prevented goals.
- Implement **positioning only**. Its estimated effect is larger; independence
  is unestablished because positioning also changes clearance eligibility and
  contacts. See `OFFLINE_FINDINGS.md` and per-goal `offline-estimates.json`.

## Changes and scope

- `team/src/keeper_geometry.py`: goal-angle bisector, 0.3 m close-ball standoff
  down to the existing 0.15 m backstop, incoming projection on that depth line.
  Preserve the existing post limits and lateral anti-inactivity shuffle.
- `team/src/main.py`: new helper only in the normal-play, non-clearing keeper
  branch. `param.py`: one keeper-only standoff constant.
- `scripts/estimate_keeper_options.py`: input cross-check and both offline
  estimates. Two test files add 15 tests.

Field-player files, scoring, throw-in handoff, opponent exit, all restart/READY/
STOP dispatch, clearance targeting/eligibility and speed/acceleration caps are
unchanged. V13's rejected speed-cap exemption is not included. The scope audit
checks 43 protected team files byte-for-byte and the remaining dispatch AST.

## Matches

Scores are ours–sample. F/W = our fallen penalties / warning events.

| Match | Side | Batch 01 | F/W | Batch 02 | F/W |
|---|---|---:|---:|---:|---:|
| 01 | Home | 3–0 | 1/0 | 3–3 | 0/0 |
| 02 | Away | 2–1 | 0/0 | 1–1 | 0/0 |
| 03 | Home | 4–0 | 0/0 | 1–1 | 0/0 |
| 04 | Away | 3–2 | 0/0 | 1–1 | 0/0 |
| 05 | Home | 3–1 | 0/0 | 1–1 | 0/0 |
| 06 | Away | 2–3 | 0/0 | 2–2 | 0/1 |
| 07 | Home | 2–2 | 0/0 | 2–1 | 0/0 |
| 08 | Away | 3–2 | 0/0 | 4–1 | 1/0 |

| Version | Games | W/D/L | GF–GA | Mean GD | GF/game | GA/game | Falls |
|---|---:|---|---|---:|---:|---:|---:|
| V11 baseline | 16 | 8/3/5 | 37–29 | +0.5000 | 2.3125 | 1.8125 | 1 |
| V14 batch 01 | 8 | 6/1/1 | 22–11 | +1.3750 | 2.7500 | 1.3750 | 1 |
| V14 batch 02 | 8 | 2/6/0 | 15–11 | +0.5000 | 1.8750 | 1.3750 | 1 |
| **V14 combined** | **16** | **8/7/1** | **37–22** | **+0.9375** | **2.3125** | **1.3750** | **2** |

### Our warning events by type

| Type | V11 | V14 |
|---|---:|---:|
| Avoidance-radius retake | 1 | 0 |
| Defender-interference retake | 1 | 0 |
| Stuck-ball advisory | 1 | 0 |
| Disallowed kickoff goal | 0 | 1 |
| Disallowed indirect goal | 0 | 0 |
| **Total** | **3** | **1** |

The kickoff warning was batch 02/match 06 at 459.800 s. Both fallen penalties
(b01/m01 at 173.286 s, b02/m08 at 10.696 s) involved roamer 3. All three
inactivity penalties also involved roamer 3 (b01/m01 at 556.900 s, m02 at
431.538 s, m03 at 140.984 s). No keeper fall or inactivity penalty occurred.
These are recorded incidents, not diagnosed mechanical causes. No out-of-scope
field-player or restart fixes were made.

## Checks and provenance

```text
Ran 130 tests in 0.333s

OK
```

```text
PASS: 16 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 2 animations verified
```

```text
PASS: all 37 source/config snapshots, package SHA256, simulator image and official opponent revision identical across V14 batches 01/02 and current source; no strategy changes between games
```

All games finished naturally after 600 regulation seconds, alternating home/away,
with telemetry and the same signed package. No tuning or discarded games.

Package SHA256:
`c09fb15587b036b5bb4842c83738e770418bcb9803d83c5a476a568d9e58c30d`.
Simulator image and sample revision match the prior evaluations.
Build used `bash scripts/build_team.sh` because the helper is not executable.

All **382,842 telemetry ticks** parsed with zero drops or writer errors.
**236,605 keeper waypoints** replayed exactly (maximum error zero), including
the protected restart path. On the same snapshots 166,805 normal targets differ
from the legacy helper, including 4,147 earlier-backstop samples. Eight native
stop errors during recovery are retained:

```text
RuntimeError('API call failed, code = 400')
```

All games completed; those errors are not diagnosed as causes of outcomes.
Basic repository/referee rules audit only: the Booster 3v3 skill remains
unavailable, not a full rules certification.

## Evidence

Both time-lapses validate at 14 actual frames / 12.6 seconds:

```text
/home/ubuntu/repos/booster-studio-s2/match-results/keeper-v14/batch-01/match-01/evidence/match-timelapse.webp
/home/ubuntu/repos/booster-studio-s2/match-results/keeper-v14/batch-02/match-01/evidence/match-timelapse.webp
```

The final CPU-rendered 3–0 snapshot from batch 01 was visually inspected. A still
verifies rendering, not keeper behavior throughout the game. `snapshot-final.png`
is beside the animation. Structured results, events, source/package provenance,
audits and checks are committed; raw telemetry, images, packages and signing
material remain local-only. Results are mirrored in the primary repository.
