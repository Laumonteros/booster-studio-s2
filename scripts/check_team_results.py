"""Validate retained referee evidence and produce a Markdown benchmark table."""
import hashlib
import json
import struct
from pathlib import Path

from run_team_batch import summarize


def main():
    root = Path(__file__).resolve().parents[1]
    results = root / 'match-results/team-v1'
    lines = ['# Team v1 benchmark summary', '',
             'Scores are **home–away**, not always ours first. Fouls and fallen-robot',
             'penalties are **ours/opponent**. Warnings count the whole match.',
             'Fall penalties are not a count of all physical falls.', '',
             '| Batch | Match | Our side | Score H–A | Winner | GF | GA | Fouls | Warnings | Fallen penalties |',
             '|---|---|---|---|---|---:|---:|---|---:|---|']
    aggregates = []
    animations = 0
    finished = failed = 0
    for batch in sorted(results.glob('batch-*')):
        valid = []
        failures = 0
        for match in sorted(batch.glob('match-*')):
            side = 'home' if int(match.name.split('-')[-1]) % 2 else 'away'
            if not (match / 'result.json').exists():
                assert (match / 'failure.json').exists(), f'Incomplete attempt: {match}'
                failed += 1
                failures += 1
                lines.append(f'| {batch.name} | {match.name} | {side} | FAILED before start | — | — | — | — | — | — |')
                continue
            result = json.loads((match / 'result.json').read_text())
            events = [json.loads(line) for line in (match / 'events.jsonl').read_text().splitlines()]
            assert result['status'] == 'finished' and result['isFinal']
            assert result['endReason'] == 'time_expired'
            assert result['timing']['regularDurationSeconds'] == 600
            assert abs(result['timing']['timeRemaining']) < .1
            assert result['game']['state'] == 'finished'
            assert result['teams'][side]['teamName'] == 'laumonteros_team_v1'
            assert result['teams']['away' if side == 'home' else 'home']['teamName'] == 'booster_champion_3v3'
            assert events[-1]['type'] == 'match_finished'
            assert events[-1]['source'] == 'auto_referee'
            assert len(events) == result['eventsTotal']
            assert events[-1]['eventId'] == result['finishedEventId']
            assert events[-1]['score'] == result['score']
            assert [event['sequence'] for event in events] == list(range(1, len(events) + 1))
            summary = summarize(result, events, side, match.name)
            saved = json.loads((match / 'summary.json').read_text())
            assert all(saved[key] == value for key, value in summary.items())
            assert summary['our_fouls'] == result['teams'][side]['stats']['fouls']['total']
            valid.append(summary)
            finished += 1
            lines.append(f"| {batch.name} | {match.name} | {side} | {summary['score_home_away']} | {summary['winner']} | {summary['goals_for']} | {summary['goals_against']} | {summary['our_fouls']}/{summary['opponent_fouls']} | {summary['warnings_total']} | {summary['our_fallen_penalties']}/{summary['opponent_fallen_penalties']} |")
        if valid:
            provenance = json.loads((batch / 'provenance.json').read_text())
            snapshot = json.loads((batch / 'source-snapshot.json').read_text())
            for name, expected in provenance['team_source_sha256'].items():
                data = snapshot[name].encode() if name in snapshot else (root / 'team' / name).read_bytes()
                assert hashlib.sha256(data).hexdigest() == expected, f'Source mismatch: {batch}/{name}'
            wins, draws, losses = [sum(row['outcome'] == value for row in valid) for value in ('win', 'draw', 'loss')]
            gf, ga = [sum(row[key] for row in valid) for key in ('goals_for', 'goals_against')]
            aggregates.append(f'- **{batch.name}: {wins}W/{draws}D/{losses}L**, GF–GA **{gf}–{ga}**, mean goal difference {(gf-ga)/len(valid):+.2f}/match; {failures} failures.')
        else:
            aggregates.append(f'- **{batch.name}: {failures} startup failures**, no match results; not counted as losses.')
        for evidence in sorted(batch.glob('match-*/evidence')):
            data = (evidence / 'match-timelapse.webp').read_bytes()
            assert data[:4] == b'RIFF' and data[8:12] == b'WEBP'
            assert len(data) <= 10 * 1024 * 1024
            cursor = 12
            durations = []
            while cursor + 8 <= len(data):
                kind = data[cursor:cursor + 4]
                size = int.from_bytes(data[cursor + 4:cursor + 8], 'little')
                body = data[cursor + 8:cursor + 8 + size]
                if kind == b'ANMF':
                    durations.append(int.from_bytes(body[12:15], 'little'))
                cursor += 8 + size + (size % 2)
            timestamps = json.loads((evidence / 'frames.json').read_text())
            assert len(durations) == len(timestamps) and len(durations) >= 3
            assert 0 < sum(durations) <= 30000
            hashes = []
            for label in ('start', 'middle', 'final'):
                png = (evidence / f'snapshot-{label}.png').read_bytes()
                assert png[:8] == b'\x89PNG\r\n\x1a\n'
                assert struct.unpack('>II', png[16:24]) == (960, 540)
                hashes.append(hashlib.sha256(png).hexdigest())
            assert len(set(hashes)) == 3
            assert timestamps[-1]['remaining'] <= .1 and 'finished' in timestamps[-1]['caption']
            animations += 1
            print(f'PASS: {evidence.relative_to(root)}: {len(durations)} actual frames, {sum(durations)/1000:.1f}s, {len(data)} bytes; three distinct 960x540 PNGs')
    lines += ['', '## Aggregates', ''] + aggregates + [
        '', 'Every completed game finished naturally after 600 regulation simulation seconds.',
        'See REPORT.md for interpretation, iteration details, limitations and evidence paths.', '',
    ]
    (results / 'SUMMARY.md').write_text('\n'.join(lines))
    print('\n'.join(lines))
    print(f'PASS: {finished} complete regulation results/event timelines, {failed} recorded failed launches; source provenance and summary counts match; {animations} animations verified')


if __name__ == '__main__':
    main()
