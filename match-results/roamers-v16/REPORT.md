# V16-candidate: roamer role hysteresis (not benchmarked)

Normal-play assignment now retains the current eligible attacker unless the
challenger is **more than 1.0 m closer** (V14's executed field selector used
0.3 m, not the 0.65 m in the legacy tactics helper). No minimum hold time is
used. Unavailable players are replaced immediately; phase reset, kickoff and
throw-in handoff logic are unchanged. Only role assignment changes; keeper,
locomotion, recovery, support positioning and ball prediction are untouched.
The package ID/version remain unchanged, as in V14; V16-candidate is the
experiment name, not a new SDK package identity.

## Comparison

| Version | Matches | W/D/L | GF–GA | Mean GD | Our fall penalties | Our total penalties |
|---|---:|---|---|---:|---:|---:|
| V14 | 16 | 8/7/1 | 37–22 | +0.9375 | 2 | 5 |
| V16-candidate | 0 | not measured | not measured | not measured | not measured | not measured |

V14 source: `../keeper-v14/SUMMARY.md` and `REPORT.md`. Falls here mean
referee fallen-robot penalties, not physical falling episodes. Actual falls
are not counted by these result summaries.

## Reproduction blocker

This machine has a working Docker daemon but **no images or containers**.
The historical `~/booster-studio` installation, prepared simulator image,
agent-dev build container, signed packages and raw telemetry are absent.
Consequently no build, match, before/after switches-per-match measurement or
new time-lapse was produced. Do not interpret unit tests as match evidence or
this candidate as an improvement over V14. No parameter variants were run.

V14 used two batches of eight unseeded, full 600-s matches, alternating sides,
with telemetry enabled and the same package throughout. No pinned seeds were
specified. Once the official runtime is initialized per `../../NOTES.md`, use
`scripts/build_team.sh` and `scripts/run_team_batch.py` with that configuration
and fresh batch/work directories. Capture is enabled for match 01 of each
batch through `capture_sequence.py`: actual physics frames every 45 simulation
seconds, 0.9 seconds per frame in the WebP. `capture_match.py` is the original
single-snapshot helper; `watch_match.py` observes the referee stream. Neither
is a strategy action or a tournament submission tool.

No tournament submission, simulator modification or undocumented SDK action
was made. The Booster 3v3 skill is unavailable; only the repository's basic
rules checklist was reviewed. Runtime and visual behavior remain unverified.

## Hooks

No project pre-commit configuration or active hooks existed. Installed a local
`.git/hooks/pre-commit` running `git diff --cached --check`; it is intentionally
not versioned and adds no dependency or shared configuration.
