"""Fetch a paginated public match list and both replay formats."""
import argparse
import json
import shutil

from config import PID, RAW, ROOT
from download import get, main as download
from legacy import run
from config import records, targets
from concurrent.futures import ThreadPoolExecutor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', action='store_true', help='Use committed all.json instead of fetching an updated match list')
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if args.snapshot:
        shutil.copyfile(ROOT / 'all.json', RAW / 'matches.json')
        matches = records()
        print(f'LIST OK: {len(matches)} records from committed snapshot', flush=True)
    else:
        matches = []
        page = 1
        while True:
            payload = get(f'https://api.booster.tech/api/v1/competition/matches?page={page}&page_size=100&player_id={PID}&ordering=-scheduled_at').json()
            if payload.get('code') != 0:
                raise ValueError(f'Match-list API failure on page {page}')
            batch = payload['data']['list']
            matches.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        if len({r['id'] for r in matches}) != len(matches):
            raise ValueError('Duplicate matches across API pages; retry with a stable snapshot')
        (RAW / 'matches.json').write_text(json.dumps(matches, ensure_ascii=False, indent=2))
        print(f'LIST OK: {len(matches)} public API records across {page} pages', flush=True)
    selected = targets(matches)
    if not selected:
        raise ValueError('No matches selected')
    download()
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(run, [RAW/r['id']/'detail.json' for r in selected]))
    print(f'FETCH OK: {len(selected)} selected matches; raw data in {RAW.relative_to(ROOT)}', flush=True)


if __name__ == '__main__':
    main()
