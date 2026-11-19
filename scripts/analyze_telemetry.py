"""Summarize observed player commands; never equate SDK updates with physical shots."""
import argparse
import bisect
import collections
import gzip
import json
import math
import statistics
from pathlib import Path


def distance(a, b):
    return math.dist(a[:2], b[:2])


def owner(event):
    actor = (event.get('actor') or {}).get('side')
    if event['type'] == 'set_play_retake':
        offender = (event.get('outcome') or {}).get('offendingActor') or {}
        return offender.get('side') or {'home': 'away', 'away': 'home'}.get(actor)
    return actor


def lane_distance(ball, target, opponents):
    dx, dy = target[0] - ball[0], target[1] - ball[1]
    length2 = dx * dx + dy * dy
    if length2 < 1e-8:
        return 0
    values = []
    for pose in opponents.values():
        if pose is None:
            continue
        t = ((pose[0] - ball[0]) * dx + (pose[1] - ball[1]) * dy) / length2
        if 0 < t < 1:
            values.append(distance(pose, (ball[0] + t * dx, ball[1] + t * dy)))
    return min(values, default=100)


def analyze(match):
    events = [json.loads(s) for s in (match / 'events.jsonl').read_text().splitlines()]
    rows, malformed = [], 0
    with gzip.open(match / 'telemetry.jsonl.gz', 'rt') as stream:
        for line in stream:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                if line.endswith('\n'):
                    raise
                malformed += 1
    ticks = [r for r in rows if r['type'] == 'tick']
    assert ticks and max(t['dropped'] for t in ticks) == 0, 'missing/dropped telemetry'
    assert not any(t['writer_error'] for t in ticks), 'writer failed'
    native = [r for r in rows if r['type'].startswith('native_')]
    assert native and any(p['commands'] for t in ticks for p in t['players']), 'pilot: backend not instrumented'
    times = [t['wall'] for t in ticks]
    side = 'home' if ticks[-1]['team'] == 1 else 'away'
    first, last = events[0]['wallTime'], events[-1]['wallTime']
    active = [t for t in ticks if first <= t['wall'] <= last and t['game'] and t['game']['state'] == 'PLAYING' and not t['game']['stopped']]
    sessions, opened, requests, latencies = [], {}, {}, []
    for row in native:
        robot, kind = row['robot'], row['type']
        if kind == 'native_start_request':
            requests[robot] = row['wall']
        if kind == 'native_start':
            latencies.append(row['wall'] - requests.get(robot, row['wall']))
            opened[robot] = row
        if kind in ('native_stop', 'native_stop_error') and robot in opened:
            start = opened.pop(robot)
            sessions.append(dict(robot=robot, start=start['wall'], end=row['wall'], duration=row['wall'] - start['wall'], stop_reason=row['reason'], thread=row['thread']))
    for robot, start in opened.items():
        sessions.append(dict(robot=robot, start=start['wall'], end=last, duration=last-start['wall'], stop_reason='right_censored', thread=start['thread']))
    roamer_sessions = [s for s in sessions if s['robot'] != 1 and s['start'] < last]
    reach, near, entering, kick_ticks, stop_reasons = collections.Counter(), collections.Counter(), {}, collections.Counter(), collections.Counter()
    support_distances, support_forward, role_changes, old_attacker = [], 0, 0, None
    opportunities = []
    for tick in active:
        ball = tick['ball']
        attacker = next((p['id'] for p in tick['players'] if p['role'] == 'attacker'), None)
        if old_attacker is not None and attacker is not None and attacker != old_attacker:
            role_changes += 1
        old_attacker = attacker
        if ball is None:
            continue
        for p in tick['players']:
            if p['id'] == 1 or p['pose'] is None:
                continue
            d = distance(ball, p['pose'])
            if d <= .7:
                near[p['id']] += 1
                if not entering.get(p['id'], False):
                    reach[p['id']] += 1
                    entering[p['id']] = True
            elif d > 1.2:
                entering[p['id']] = False
            if p['role'] == 'support':
                support_distances.append(d)
                support_forward += p['pose'][0] > ball[0]
            commands = [c for c in p['commands'] if c['kind'] == 'kick_body']
            if commands:
                kick_ticks[p['id']] += 1
            if commands and d <= 1.0 and distance(ball, (7, 0)) <= 4.5:
                command = commands[-1]
                heading = p['pose'][2] + command['direction']
                virtual = (p['pose'][0] + 8*math.cos(heading), p['pose'][1] + 8*math.sin(heading))
                vx, vy = virtual[0]-ball[0], virtual[1]-ball[1]
                crossing = None if vx <= 1e-6 else ball[1]+(7-ball[0])*vy/vx
                target_call = next((c for c in p['calls'] if c['method']=='attack'), None)
                target = target_call['args'][0] if target_call and target_call['args'] else (7,0)
                if target is None or target[0] < 7 or command['power'] < 5:
                    continue
                opportunities.append(dict(wall=tick['wall'], robot=p['id'], ball=ball, pose=p['pose'], target=target,
                    command=command, goal_cross_y=crossing, lane_clearance=lane_distance(ball,target,tick['opponents'])))
    for s in roamer_sessions:
        stop_reasons[s['stop_reason']] += 1

    possessions, start = [], None
    for event in events:
        if event['type'] == 'ball_touch':
            if event['actor']['side'] == side:
                if start is None:
                    start = event['wallTime']
            elif start is not None:
                possessions.append((start, event['wallTime']))
                start = None
        elif event['type'] in ('ball_placement_started','goal','match_finished') and start is not None:
            possessions.append((start,event['wallTime']))
            start = None
    possession_counts = [sum(s['start'] <= end and s['end'] >= begin for s in roamer_sessions) for begin,end in possessions]
    shooting_possessions = []
    for begin,end in possessions:
        shots = [o for o in opportunities if begin <= o['wall'] <= end]
        if shots:
            shooting_possessions.append(dict(start=begin,end=end,first=shots[0],
                goal=any(e['type']=='goal' and owner(e)==side and begin<=e['wallTime']<=end for e in events)))
    contexts = []
    for event in events:
        conceded = event['type']=='goal' and owner(event)!=side
        violation = event['severity']=='warning' or (event['type']=='penalty' and event['outcome']['reason'] in ('illegalPosition','motionInSet'))
        if conceded or violation:
            index = bisect.bisect_right(times,event['wallTime']) - 1
            snapshot = ticks[index] if index >= 0 else None
            earlier = [ticks[max(0,bisect.bisect_right(times,event['wallTime']-dt)-1)] for dt in (2,1)]
            contexts.append(dict(event=event, conceded=conceded, ours=owner(event)==side,
                observation_age=None if snapshot is None else event['wallTime']-snapshot['wall'],
                snapshot=snapshot, previous=earlier))
    intervals = [b-a for a,b in zip(times,times[1:])]
    restart_switches = []
    for a,b in zip(active,active[1:]):
        for p in b['players']:
            if p['id']==1:
                continue
            prev = next((q for q in a['players'] if q['id']==p['id']),None)
            x = next((c for c in prev['calls'] if c['method']=='attack' and c['args']),None) if prev else None
            y = next((c for c in p['calls'] if c['method']=='attack' and c['args']),None)
            if x and y and x['args'][0][0] < 7 and y['args'][0][0] >= 7 and prev['native_active'] and p['native_active']:
                restart_switches.append(dict(before=a,after=b,robot=p['id']))
    aggregate = dict(side=side,ticks=len(ticks),playing_ticks=len(active),native_events=len(native),malformed_lines=malformed,
        roamer_reach_episodes=dict(reach),roamer_near_ball_ticks=dict(near),roamer_kick_command_ticks=dict(kick_ticks),
        roamer_sessions=len(roamer_sessions),session_duration_median=statistics.median(s['duration'] for s in roamer_sessions) if roamer_sessions else None,
        sessions_under_1s=sum(s['duration']<1 for s in roamer_sessions),session_stop_reasons=dict(stop_reasons),
        native_errors=sum(r['type'].endswith('_error') for r in native),start_latency_max=max(latencies,default=0),
        role_changes=role_changes,referee_touch_possessions=len(possessions),sessions_per_possession=possession_counts,
        support_distance_median=statistics.median(support_distances) if support_distances else None,
        support_forward_ticks=support_forward,support_ticks=len(support_distances),
        close_in_range_kick_ticks=len(opportunities),blocked_kick_ticks=sum(o['lane_clearance']<.45 for o in opportunities),
        virtual_ray_outside_goal_ticks=sum(o['goal_cross_y'] is None or abs(o['goal_cross_y'])>1.25 for o in opportunities),
        shooting_possessions=len(shooting_possessions),shooting_possessions_scored=sum(p['goal'] for p in shooting_possessions),
        shooting_possessions_initially_blocked=sum(p['first']['lane_clearance']<.45 for p in shooting_possessions),
        conceded_goals=sum(c['conceded'] for c in contexts),our_warning_events=sum(c['event']['severity']=='warning' and c['ours'] for c in contexts),
        tick_gap_max=max(intervals,default=0),tick_gaps_over_200ms=sum(dt>.2 for dt in intervals),
        restart_aim_switches_without_release=len(restart_switches),dropped=max(t['dropped'] for t in ticks))
    return dict(aggregate=aggregate,sessions=roamer_sessions,event_contexts=contexts,shooting_possessions=shooting_possessions,opportunity_samples=opportunities[::max(1,len(opportunities)//50)],restart_switches=restart_switches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch',type=Path)
    args = parser.parse_args()
    for match in sorted(args.batch.glob('match-*')):
        if not (match/'result.json').exists():
            continue
        report = analyze(match)
        (match/'telemetry-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
        print(match.name,json.dumps(report['aggregate'],indent=2))


if __name__=='__main__':
    main()
