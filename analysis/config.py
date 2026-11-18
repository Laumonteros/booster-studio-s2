"""Paths resolve relative to these scripts, not the caller's working directory."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = Path(os.environ.get('ANALYSIS_OUTPUT', str(ROOT))).resolve()
PID = '8b44c8b4-aa9d-4511-8513-1a1ef4f6114e'


def records():
    path = RAW / 'matches.json'
    return json.loads((path if path.exists() else ROOT / 'all.json').read_text())


def targets(matches):
    selected = os.environ.get('MATCH_IDS')
    if selected:
        ids = set(selected.split(','))
        found = [r for r in matches if r['id'] in ids]
        if len(found) != len(ids):
            raise ValueError('Some MATCH_IDS were not found in the match list')
        return found
    return [r for r in matches if r['source'] == 'OFFICIAL' and (r.get('season') or {}).get('code') == 'S1'] + sorted(
        [r for r in matches if r['source'] == 'FREE_BATTLE'],
        key=lambda r: r['scheduled_at'], reverse=True)[:20]
