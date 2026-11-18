"""Local operator harness; never imported by a submitted strategy.

Requires the prepared official runtime image from NOTES.md and a built team
package. All clocks use the unmodified 600-second referee defaults.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path


def command(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, text=True, capture_output=True, **kwargs).stdout.strip()


def request(port, endpoint, post=False):
    req = urllib.request.Request(f'http://127.0.0.1:{port}/{endpoint}', method='POST' if post else 'GET')
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def summarize(result, events, side, name):
    other = 'away' if side == 'home' else 'home'
    penalties = [e for e in events if e['type'] == 'penalty']
    warnings = result.get('warnings', [])
    gf, ga = result['score'][side], result['score'][other]
    return {
        'match': name, 'side': side, 'status': result['status'],
        'score_home_away': f"{result['score']['home']}-{result['score']['away']}",
        'goals_for': gf, 'goals_against': ga,
        'outcome': 'win' if gf > ga else 'loss' if gf < ga else 'draw',
        'winner': result['winner'], 'end_reason': result['endReason'],
        'our_fouls': sum(e.get('actor', {}).get('side') == side for e in penalties),
        'opponent_fouls': sum(e.get('actor', {}).get('side') == other for e in penalties),
        'our_fallen_penalties': sum(e.get('actor', {}).get('side') == side and e.get('outcome', {}).get('reason') == 'fallenRobot' for e in penalties),
        'opponent_fallen_penalties': sum(e.get('actor', {}).get('side') == other and e.get('outcome', {}).get('reason') == 'fallenRobot' for e in penalties),
        'warnings_total': len(warnings),
        'our_warning_events': sum(warning_offender(e) == side for e in events if e.get('severity') == 'warning'),
        'regular_seconds': result['timing']['regularDurationSeconds'],
        'wall_seconds': round(result['durationSeconds'], 1),
    }


def warning_offender(event):
    actor = (event.get('actor') or {}).get('side')
    if event['type'] != 'set_play_retake':
        return actor
    offender = (event.get('outcome', {}).get('offendingActor') or {}).get('side')
    return offender or {'home': 'away', 'away': 'home'}.get(actor)


def run_match(index, args):
    side = 'home' if index % 2 else 'away'
    name = f'match-{index:02}'
    container = f'bs-team-{args.batch}-{index:02}'
    port = args.base_port + index
    work = args.work / args.batch / name
    destination = args.output / args.batch / name
    work.mkdir(parents=True, exist_ok=False)
    destination.mkdir(parents=True, exist_ok=False)
    runner = capture = None
    row = None
    try:
        home = 'laumonteros_team_v1' if side == 'home' else 'booster_champion_3v3'
        away = 'booster_champion_3v3' if side == 'home' else 'laumonteros_team_v1'
        command('docker', 'run', '-d', '--name', container, '--privileged', '--cgroupns=private', '--shm-size=512m',
                '-p', f'127.0.0.1:{port}:38383', '-v', f'{work}:/match/results',
                '-e', 'MODEL_PATH=mjcf/football_match_pitch_6_K1.xml',
                '-e', f'MATCH_ID={args.batch}-{name}', '-e', 'MATCH_RESULT_DIR=/match/results',
                '-e', 'GAME_CONTROL_REQUIRE_TEAM_READY=false', '-e', 'GAME_CONTROL_AUTO_START=false',
                '-e', 'GAME_CONTROL_EXIT_ON_FINISH=false',
                '-e', f'GAME_CONTROL_INITIAL_HOME_TEAM_NAME={home}',
                '-e', f'GAME_CONTROL_INITIAL_AWAY_TEAM_NAME={away}', args.image)
        command('docker', 'cp', args.package, f'{container}:/tmp/team.agent')
        command('docker', 'exec', container, 'python3', '-c',
                "import zipfile;from pathlib import Path; p=Path('/opt/booster/booster_agent_data/data/agents/extract/laumonteros_team_v1'); zipfile.ZipFile('/tmp/team.agent').extractall(p); (p/'agent/laumonteros_team_v1/lib/laumonteros_team_v1/pyagent_x86_64').chmod(0o755)")
        # The original sample was extracted with Python too, so restore its bit.
        command('docker', 'exec', container, 'chmod', '+x', '/opt/booster/booster_agent_data/data/agents/extract/booster_champion_3v3/agent/booster_champion_3v3/lib/booster_champion_3v3/pyagent_x86_64')
        deadline = time.monotonic() + 240
        while True:
            try:
                if request(port, 'health').get('ready'):
                    break
            except (OSError, ValueError):
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('Simulator startup did not become ready within 240s')
            time.sleep(1)
        with (work / 'teams.log').open('w') as log:
            runner = subprocess.Popen(['docker', 'exec', container, 'python3', '/opt/local-3v3-runner/run.py', '--teams', home, away, '--publish-logs'], stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 240
        while True:
            if runner.poll() is not None:
                raise RuntimeError(f'Team runner exited with {runner.returncode}; see {work}/teams.log')
            active = (work / 'teams.log').read_text().count('Inactive=>Active') == 2
            try:
                healthy = request(port, 'health').get('ready')
            except (OSError, ValueError):
                healthy = False
            if active and healthy:
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Both team activation and referee readiness required within 240s')
            time.sleep(1)
        started = request(port, 'match/start', post=True)
        (work / 'operator-start.json').write_text(json.dumps(started, indent=2))
        print(f'{args.batch}/{name}: started 600s match, ours={side}, both teams Active', flush=True)
        if index == 1 and not args.no_capture:
            script = Path(__file__).with_name('capture_sequence.py')
            command('docker', 'cp', script, f'{container}:/usr/local/booster_robot/booster_robocup_sim/capture_sequence.py')
            with (work / 'capture.log').open('w') as log:
                capture = subprocess.Popen(['docker', 'exec', '-e', 'MUJOCO_GL=egl', '-e', 'LIBGL_ALWAYS_SOFTWARE=1', '-w', '/usr/local/booster_robot/booster_robocup_sim', container, '.venv/bin/python', 'capture_sequence.py'], stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + args.timeout
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/events', timeout=180) as response:
            for raw in response:
                if time.monotonic() > deadline:
                    raise TimeoutError('Full-match wall timeout exceeded; no manual end issued')
                if runner.poll() is not None:
                    raise RuntimeError(f'Team runner exited during match: {runner.returncode}')
                if not raw.startswith(b'data:'):
                    continue
                data = json.loads(raw[5:])
                if data.get('isFinal'):
                    result = data
                    break
            else:
                raise RuntimeError('Referee stream ended without a final result')
        if result['endReason'] != 'time_expired' or result['timing']['regularDurationSeconds'] != 600:
            raise RuntimeError('Result was not a complete regulation match')
        deadline = time.monotonic() + 30
        while True:
            try:
                authoritative = json.loads((work / 'result.json').read_text())
                if authoritative.get('isFinal'):
                    break
            except (OSError, ValueError):
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('Final SSE observed but authoritative file was not finalized within 30s')
            time.sleep(.1)
        assert authoritative['matchId'] == result['matchId'] and authoritative['score'] == result['score']
        shutil.copyfile(work / 'result.json', destination / 'result.json')
        shutil.copyfile(work / 'events.jsonl', destination / 'events.jsonl')
        events = [json.loads(line) for line in (destination / 'events.jsonl').read_text().splitlines()]
        row = summarize(result, events, side, name)
        if capture is not None:
            capture.wait(timeout=180)
            if capture.returncode:
                row['capture_error'] = f'Capture exited {capture.returncode}; see {work}/capture.log'
            else:
                evidence = destination / 'evidence'
                evidence.mkdir()
                for filename in ('match-timelapse.webp', 'snapshot-start.png', 'snapshot-middle.png', 'snapshot-final.png', 'frames.json'):
                    shutil.copyfile(work / 'evidence' / filename, evidence / filename)
        (destination / 'summary.json').write_text(json.dumps(row, indent=2))
        print(f'{args.batch}/{name}: {row}', flush=True)
    except Exception as exc:
        row = {'match': name, 'side': side, 'status': 'failed', 'error': str(exc)}
        if (work / 'teams.log').exists():
            row['runner_tail'] = (work / 'teams.log').read_text().splitlines()[-20:]
        (destination / 'failure.json').write_text(json.dumps(row, indent=2))
        print(f'{args.batch}/{name}: FAILED {exc}', flush=True)
    finally:
        try:
            (work / 'container.log').write_text(command('docker', 'logs', container))
        except subprocess.CalledProcessError:
            pass
        subprocess.run(['docker', 'stop', '-t', '10', container], capture_output=True)
        for process in (runner, capture):
            if process is not None:
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.terminate()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--image', default='booster-studio-local:prepared')
    parser.add_argument('--output', type=Path, default=Path('match-results/team-v1'))
    parser.add_argument('--work', type=Path, default=Path.home() / 'booster-studio/team-v1-runs')
    parser.add_argument('--batch', required=True)
    parser.add_argument('--matches', type=int, default=4)
    parser.add_argument('--workers', type=int, choices=(1, 2), default=2)
    parser.add_argument('--base-port', type=int, default=38400)
    parser.add_argument('--timeout', type=float, default=7200)
    parser.add_argument('--no-capture', action='store_true')
    args = parser.parse_args()
    args.package = args.package.resolve(strict=True)
    args.output, args.work = args.output.resolve(), args.work.resolve()
    if args.matches < 4:
        parser.error('At least four full matches are required')
    if (args.output / args.batch).exists() or (args.work / args.batch).exists():
        parser.error('Batch paths already exist; use a new batch identifier')
    args.output.mkdir(parents=True, exist_ok=True)
    provenance = {
        'image': command('docker', 'image', 'inspect', args.image, '--format', '{{.Id}}'),
        'package_sha256': hashlib.sha256(args.package.read_bytes()).hexdigest(),
        'workers': args.workers, 'matches': args.matches,
        'team_source_sha256': {str(p.relative_to(Path('team'))): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('team').rglob('*.py'))},
        'sample_revision': '36f0d615af6fd5f7d5475570e27daa3b3ec97632',
    }
    source_snapshot = {name: (Path('team') / name).read_text() for name in (
        'agent.toml', 'src/main.py', 'src/player.py', 'src/param.py', 'src/tactics.py',
    )}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(lambda i: run_match(i, args), range(1, args.matches + 1)))
    batch = args.output / args.batch
    (batch / 'provenance.json').write_text(json.dumps(provenance, indent=2))
    (batch / 'source-snapshot.json').write_text(json.dumps(source_snapshot, indent=2))
    (batch / 'summary.json').write_text(json.dumps(rows, indent=2))
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (batch / 'summary.csv').open('w') as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    valid = [r for r in rows if r['status'] == 'finished']
    print(f'BATCH COMPLETE: {len(valid)}/{len(rows)} finished; W/D/L=' + '/'.join(str(sum(r['outcome'] == v for r in valid)) for v in ('win', 'draw', 'loss')), flush=True)
    if len(valid) != len(rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
