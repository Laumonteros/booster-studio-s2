# Startup race — no games started

All four attempted launches failed before either strategy ran. The harness
started the official team runner before the runtime's agent manager existed.
Each runner's traceback ended with:

```text
  File "/opt/local-3v3-runner/run.py", line 253, in main
    load_runtime_env()
  File "/opt/local-3v3-runner/run.py", line 122, in load_runtime_env
    raise RuntimeError("booster_agent_manager process not found")
RuntimeError: booster_agent_manager process not found
```

No match-start request was issued and there is no final match result for these
four attempts. They are infrastructure failures, not losses. Per-attempt
`failure.json` and aggregate `summary.json` retain their original outcomes.
Full local logs: `/home/ubuntu/booster-studio/team-v1-runs/batch-01/match-*/teams.log`.

The harness now waits for the running referee's readiness endpoint before
launching the teams, then separately verifies both agents are Active before
starting the match. The next batch uses a new identifier; no failed attempt
was overwritten or counted as a completed game.
