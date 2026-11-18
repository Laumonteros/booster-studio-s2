# 月月 champion replay analysis

Public Booster Studio 3v3 match/replay analysis for player
`8b44c8b4-aa9d-4511-8513-1a1ef4f6114e`. Read the
[findings, methods and caveats](champion_analysis.md).

## Key findings (five lines)

1. S1: 16–1–4, 80–51 goals; all seven group/knockout games were wins.
2. The recurring formation is one deep goalkeeper and two roaming field robots.
3. Keeper numbers vary across S1; recent arena uses #3 in 17/20 matches.
4. Nearest-ball share is not possession: recent losses have higher proximity share than wins.
5. Recent arena fouls are dominated by fallen robots (53/63), a recovery-discipline weakness.

## Fetch and rerun

Python 3.10+; commands below run **from this directory**. Paths in scripts are
relative to the scripts, so invocation from elsewhere also works.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python fetch.py --snapshot
.venv/bin/python analyze.py
.venv/bin/python report.py
```

`--snapshot` reuses committed `all.json` (371 records, including one failed
start) to reproduce the November 18 analysis. Without it, `fetch.py` downloads
all match-list pages from the public API, then fetches S1 official plus the
latest 20 arena replays. No credentials are needed. Old S1 matches use ZIPs;
modern matches use gzip JSONL segments. Downloads, API details, status logs
and 2-Hz frame samples live only in **gitignored `data/raw/`**. Fetches reuse
existing files; remove that directory to refresh replay metadata/URLs. Full
fetches can use substantial disk/network resources (hundreds of MB).

`analyze.py` regenerates the CSVs and three PNGs in this directory. It rejects
missing segments instead of silently computing partial matches. Unavailable
replays are recorded in `coverage.csv`. Two malformed upstream frame lines
are skipped and logged in `data/raw/malformed_frames.log`.

**The Markdown narrative is curated for this snapshot**, not an automatic
interpretation of arbitrary new matches. `report.py` refreshes its tables but
refuses partial/changed-size selections; retain the committed snapshot to
reproduce it. If using a newer list, review/update narrative claims manually.

## Small clean-state verification

Use one legacy S1 and one modern arena match, with outputs isolated from the
committed full analysis. Start without `data/raw/` to exercise actual downloads:

```sh
export MATCH_IDS=9b8045df-ea1a-4b73-94b4-2ad8562637eb,24731c1e-d307-48f1-b625-1cb1764d0e1d
export ANALYSIS_OUTPUT="$PWD/data/test-output"
.venv/bin/python fetch.py
.venv/bin/python analyze.py
.venv/bin/python verify.py
unset MATCH_IDS ANALYSIS_OUTPUT
```

This checks public match-list pagination, both replay download formats and
metrics/goal reconciliation against the committed full-run CSVs. If the public
match list changes, use `fetch.py --snapshot` for a stable comparison.

## Committed outputs

- `all.json`: small public match-list snapshot, not raw replay downloads.
- `records.csv`, `record_summary.csv`, `opponents.csv`: all completed results.
- `robots.csv`, `teams.csv`, `goals.csv`, `goal_trajectories.csv`,
  `fouls_by_reason.csv`, `coverage.csv`: per-match/robot/goal derived data.
- `robot_summary.csv`, `role_summary.csv`, `team_summary.csv`: grouped metrics.
- `robots_OFFICIAL.png`, `robots_FREE_BATTLE.png`, `ball_heatmaps.png`: role and
  ball distributions, all normalized to attack +x.

Coverage: 20/21 S1 + 20/20 arena replays; missing S1 UUID
`75d85417-6c32-4f56-87cd-74987577891f` (3–0 win). Event/replay alignment is
approximate (~1 second); near-ball labels are not proven scorers. The own-box
region is an operational coordinate proxy, not verified official geometry.
