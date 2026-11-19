# Defense V13 — do not merge

Base: `origin/main` / V11, `6c2c637b848e62291d2ae42b6e971226a0301f59`.
Branch: `devin/defense-v13`. No PR.

**The candidate failed its objective.** Over 16 games, GA/game increased
1.8125 -> 2.0000, mean GD decreased +0.5000 -> +0.2500, and fallen penalties
increased 1 -> 4. Push for retention, not as a recommended merge.

## Evidence and the one change

`CONCEDED_FINDINGS.md` gives methodology, limitations, counterevidence and the
reachable dispatch chain. `GOALS.csv` classifies every one of the **57 goals
against in V9/V11's 32 games**; the JSON audit retains the underlying snapshots.

Ranked mutually exclusive observational groups:

1. **30:** keeper lateral coverage miss, ball crossing >0.45 m from the keeper.
2. **24:** goal despite crossing within 0.45 m of the keeper.
3. **1:** keeper recovering/unavailable.
4. **1:** keeper out of goal position, behind the goal line.
5. **1:** no sufficiently contiguous observed keeper-plane crossing.

These are measured failure groups, not proven physical causes. The 0.45 m
band is not a verified save radius. Last attack lead-ins: **19** opponent
recoveries after recorded keeper contacts, **18** defensive-third turnovers,
**9** restart touches, **8** middle-third turnovers, **2** restarts without
recorded later turnovers, **1** attacking-third turnover. The 19 keeper
contacts do not establish 19 saved-shot rebounds; two have recent clearing
actions, but none proves an early clearing commitment caused the goal.

For every goal, the CSV includes turnover location, release-proximity range
and angle, keeper and both roamers' poses, keeper crossing/status and own
contact flags. Shot origins are last fresh opponent-proximity observations,
**not observed physical shots**. Median range 1.565 m; range bins <=2 / >2–4.5 /
>4.5 m: **35/16/6**. Angle bins <=20 / >20–45 / >45 degrees: **12/6/39**.
**33** goals have own-side final recorded contact, but contact coalescing means
exact final own robot and deflection-versus-miskick cannot always be identified.

In **11 of the 30 lateral misses**, a keeper incoming-intercept target was
within 0.30 m of the eventual crossing y, while an accepted movement command
was saturated at the nearby-robot half-speed limit. All **477,422** historical
keeper waypoints replay exactly from public observations. The limiter's effect
on those requests is verified; the counterfactual that more speed prevents
the goals is not. Counterevidence: **264 of 499** saturated intercept samples
are outside four-wall-second conceded-goal windows, and 19 lateral misses
lack a verified correct-target binding-cap sample.

The only runtime edit is in `team/src/player.py`: **robot 1 with action
`keeper:intercept` is exempt from the nearby-robot speed multiplier**. The
1.5 m/s maximum, turn-related reduction, acceleration limits and immediate
stops remain. Tracking/patrol, clearing, READY/restarts and recovery filters
retain their behavior. Field-player scoring, support, throw-in handoff,
opponent exit, keeper geometry, parameters and framework are unchanged.

The intervention addresses a demonstrated controller restriction inside the
largest measured failure group; it is not evidence that restriction caused
all 30 goals. No second defensive change or between-batch tuning was made.

## Per-match results

Scores are **ours–sample**. F/W = our fallen penalties / own warning events.

| Match | Side | Batch 01 | F/W | Batch 02 | F/W |
|---|---|---:|---:|---:|---:|
| 01 | Home | 4–1 | 0/0 | 3–0 | 0/0 |
| 02 | Away | 2–3 | 0/0 | 2–3 | 1/0 |
| 03 | Home | 3–3 | 0/0 | 2–1 | 2/0 |
| 04 | Away | 3–3 | 0/0 | 1–2 | 0/0 |
| 05 | Home | 4–1 | 0/0 | 2–1 | 0/0 |
| 06 | Away | 0–7 | 0/0 | 3–0 | 0/0 |
| 07 | Home | 2–1 | 0/0 | 1–2 | 1/1 |
| 08 | Away | 2–2 | 0/0 | 2–2 | 0/0 |

| Version/batch | Games | W/D/L | GF–GA | Mean GD | GF/game | GA/game | Falls |
|---|---:|---|---|---:|---:|---:|---:|
| V11 baseline | 16 | 8/3/5 | 37–29 | +0.5000 | 2.3125 | 1.8125 | 1 |
| V13 batch 01 | 8 | 3/3/2 | 20–21 | -0.1250 | 2.5000 | 2.6250 | 0 |
| V13 batch 02 | 8 | 4/1/3 | 16–11 | +0.6250 | 2.0000 | 1.3750 | 4 |
| **V13 combined** | **16** | **7/4/5** | **36–32** | **+0.2500** | **2.2500** | **2.0000** | **4** |

Mean GD regressed **0.25/game**. The 0–7 match is included, with no outlier
removal. Static scoring behavior was unchanged, but scoring output is not
guaranteed unchanged when defensive interactions change.

### Our warnings by type

| Type | V11 | V13 |
|---|---:|---:|
| Avoidance-radius retake | 1 | 0 |
| Defender-interference retake | 1 | 1 |
| Stuck-ball reset advisory | 1 | 0 |
| Disallowed indirect/kickoff goal | 0 | 0 |
| **Total** | **3** | **1** |

V13's warning is batch-02/match-07 at 403.870 s, player 2. Other own penalties:
**five inactivity, four fallen-robot, one motion-in-SET**, plus that one
defender interference. Fallen penalties are not all physical falls. Falls:

- Batch 02/02, player 3, 313.842 s.
- Batch 02/03, keeper 1, 139.924 s; player 2, 140.952 s.
- Batch 02/07, player 2, 35.704 s.

Thus **one keeper and three roamer fallen penalties**. The keeper's last
active recorded label before recovery was `keeper:track`; that does not
establish whether earlier interception/motion/contact caused the fall.
The physical causes of these penalties and the overall regression are not
verified. `incident-contexts.json` preserves events and preceding observations.

## Runtime, provenance and resumption

All **16/16 games** ended naturally after **600 regulation seconds**, alternating
home/away in both batches, with telemetry. **Zero failed launches**. On resume,
matches 01–04 were valid completed games and 05–06 were still live: the
original harness and runtime survived the interruption. It finished both
batches normally. No incomplete game needed discarding, and none was rerun.

`runtime-audit.json`: **410,193 ticks**, zero dropped records/writer errors.
The code change was exercised: **177 accepted incoming keeper commands**
exceed the old contact cap, among **757 crowded intercept ticks**. These are
command samples, not shots or confirmed saves. Seven native stop errors were
retained, all on field robots 2/3 during recovering/stopping release:

```text
RuntimeError('API call failed, code = 400')
```

All games completed; those errors are not diagnosed as causes of the result.

Frozen package SHA256:
`6c44035917fbe25c66524c35b5cab748389c372f5f934b0af56ad2892120c719`.
The two source snapshots, image, package and official sample revision match
exactly. `provenance-check.txt` includes the cross-batch/current-source check.
No V12 support change was carried over.

## Checks

Full existing unit suite plus eleven added tests:

```text
Ran 126 tests in 0.249s

OK
```

```text
PASS: 16 complete regulation results/event timelines, 0 recorded failed launches; source provenance and summary counts match; 2 animations verified
```

```text
PASS: all 36 source/config snapshot entries, package SHA256, simulator image and official opponent revision identical across V13 batches 01/02 and current source; no strategy changes between games
```

`git diff --check` produced no errors. `scripts/build_team.sh` was invoked
with `bash` because the checked-in script is not executable; no build-config
changes were needed. The existing simulator setup survived, so no reinstall
was performed. Booster 3v3 skill remains unavailable: this is a basic
repository/referee audit, not full skill-based rules certification.

## Evidence paths

Mirrored under `/home/ubuntu/repos/booster-studio-s2/match-results/defense-v13/`:

- `batch-01/match-01/evidence/match-timelapse.webp`: **13 frames, 11.7 s**.
- `batch-02/match-01/evidence/match-timelapse.webp`: **14 frames, 12.6 s**.

The final CPU-rendered **4–1** snapshot was visually inspected. That verifies
rendering, not the keeper-speed intervention's physical effectiveness. Raw
compressed telemetry, visual binaries, packages and signing material remain
local-only. Structured analyses, referee timelines/results and source
provenance are retained in git.
