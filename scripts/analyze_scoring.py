"""Offline last-touch chance proxies; SDK updates are not physical shots."""
import argparse
import collections
import gzip
import json
import math
from pathlib import Path

from analyze_telemetry import lane_distance


def analyze(match):
    events = list(map(json.loads, (match/'events.jsonl').read_text().splitlines()))
    side = json.loads((match/'summary.json').read_text())['side']
    episodes, active, pending = [], None, None
    for event in events:
        if event['type'] == 'ball_touch':
            pending = None
            if event['actor']['side'] == side:
                if active is None:
                    active = dict(start=event['wallTime'], near=[], far=0, chance_ticks=0)
            elif active is not None:
                active.update(end=event['wallTime'], end_type='opponent_touch', goal=False)
                episodes.append(active)
                pending = active
                active = None
        elif event['type'] in ('goal', 'ball_placement_started', 'match_finished'):
            if active is not None:
                active.update(end=event['wallTime'], end_type=event['type'],
                              goal=event['type']=='goal' and event['actor']['side']==side)
                episodes.append(active)
                active = None
            elif pending is not None and event['type']=='goal' and event['actor']['side']==side:
                pending.update(goal=True, goal_after_deflection=True, goal_wall=event['wallTime'])
            pending = None
    index = 0
    support_distances = []
    with gzip.open(match/'telemetry.jsonl.gz', 'rt') as stream:
        for tick in map(json.loads, stream):
            if tick['type'] != 'tick':
                continue
            assert tick['dropped']==0 and tick['writer_error'] is None
            while index < len(episodes) and tick['wall'] > episodes[index]['end']:
                index += 1
            if index==len(episodes):
                break
            ep = episodes[index]
            game, ball = tick['game'], tick['ball']
            if (tick['wall'] < ep['start'] or game is None or ball is None
                    or game['state']!='PLAYING' or game['stopped']
                    or game['set_play']!='NONE' or game['kicking_team']!=255 or game['secondary']>0):
                continue
            in_range = math.dist(ball[:2], (7,0)) <= 4.5
            ep['chance_ticks'] += int(in_range)
            for player in tick['players']:
                if player['id']==1 or player['pose'] is None:
                    continue
                if in_range and player['action']=='support':
                    gap=math.dist(player['pose'][:2],ball[:2])
                    support_distances.append(gap)
                    ep['last_support']=dict(wall=tick['wall'],gap=gap)
                if player['action']!='attack' or math.dist(player['pose'][:2],ball[:2])>.8:
                    continue
                commands=[c for c in player['commands'] if c['kind']=='kick_body']
                if not commands:
                    continue
                if not in_range:
                    ep['far'] += 1
                    continue
                center_y = ball[1]+(7-ball[0])*(-ball[1])/(7.25-ball[0]) if abs(7.25-ball[0])>1e-9 else ball[1]
                clearance = lane_distance(ball, (7,center_y), tick['opponents'])
                alternative = max(lane_distance(ball,(7,y),tick['opponents']) for y in (-1.,1.))
                ep['near'].append(dict(wall=tick['wall'],ball=ball,pose=player['pose'],
                                       opponents=tick['opponents'],center_clearance=clearance,
                                       alternative_clearance=alternative))
    counts=collections.Counter()
    for ep in episodes:
        counts['last_touch_possessions']+=1
        counts['possessions_with_far_close_ball_requests']+=bool(ep['far'])
        if not ep['chance_ticks']:
            continue
        counts['in_range_possessions']+=1
        counts['goals_credited_after_opponent_deflection']+=ep.get('goal_after_deflection',False)
        if ep['goal']:
            label='scored'
        elif not ep['near']:
            label='no_close_in_range_request'
        elif all(s['center_clearance']<.45 for s in ep['near']):
            label='all_close_requests_center_blocked'
        else:
            label='had_clear_center_request_not_scored'
        ep['classification']=label
        counts[label]+=1
        if ep['near']:
            counts['close_request_possessions']+=1
            counts['initially_blocked']+=ep['near'][0]['center_clearance']<.45
            counts['all_center_blocked_with_clear_alternative']+=label=='all_close_requests_center_blocked' and any(s['alternative_clearance']>=.45 for s in ep['near'])
            counts['scored_despite_all_center_requests_blocked']+=label=='scored' and all(s['center_clearance']<.45 for s in ep['near'])
        support=ep.get('last_support')
        if not ep['goal'] and ep['end_type']=='opponent_touch' and support and ep['end']-support['wall']<.2:
            counts['opponent_recoveries_with_fresh_support_sample']+=1
            counts['opponent_recoveries_support_over_2_5m']+=support['gap']>2.5
        for sample in ep['near']:
            counts['close_request_ticks']+=1
            counts['center_blocked_ticks']+=sample['center_clearance']<.45
            counts['center_blocked_clear_alternative_ticks']+=sample['center_clearance']<.45 and sample['alternative_clearance']>=.45
        ep['near_count']=len(ep['near'])
        ep['near']=ep['near'][::max(1,len(ep['near'])//3)][:4]
    return dict(match=str(match), counts=dict(counts), episodes=episodes,
                support_distance_samples=support_distances[::max(1,len(support_distances)//100)])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    reports=[analyze(p.parent) for p in sorted(args.results.glob('batch-*/match-*/summary.json'))]
    counts=collections.Counter()
    for report in reports:
        counts.update(report['counts'])
    args.output.write_text(json.dumps(dict(totals=dict(counts),matches=reports),indent=2)+'\n')
    print(json.dumps(dict(counts),indent=2))


if __name__=='__main__':
    main()
