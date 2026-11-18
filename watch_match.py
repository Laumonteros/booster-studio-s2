"""Wait for the local referee's final SSE status without changing the match."""
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent
with urllib.request.urlopen("http://127.0.0.1:38383/events", timeout=1800) as response:
    with (root / "match-events.sse").open("w") as log:
        for raw in response:
            line = raw.decode()
            log.write(line)
            log.flush()
            if not line.startswith("data:"):
                continue
            data = json.loads(line[5:])
            if data.get("isFinal"):
                (root / "final-match-status.json").write_text(json.dumps(data, indent=2))
                print(json.dumps(data, indent=2), flush=True)
                break
        else:
            raise RuntimeError("Referee stream closed without a final match status")
