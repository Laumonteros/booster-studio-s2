"""Measure actual support spacing separately from commanded target geometry."""
import argparse
import gzip
import json
import math
import statistics
from pathlib import Path


def summary(values):
    if not values:
        return {'samples': 0}
    ordered = sorted(values)
    return dict(samples=len(values), median=statistics.median(values),
                p10=ordered[int(.1*(len(ordered)-1))], p90=ordered[int(.9*(len(ordered)-1))],
                fraction_1_5_to_2_5=sum(1.5<=x<=2.5 for x in values)/len(values))


def distances(path):
    ball_dist, carrier_dist, target_dist, own_ball_dist, own_target_dist = [],[],[],[],[]
    near_carrier_dist = []
    ticks, native, dropped, malformed = 0,0,0,0
    with gzip.open(path,'rt') as f:
        for line in f:
            try:
                t=json.loads(line)
            except json.JSONDecodeError:
                if line.endswith('\n'):
                    raise
                malformed+=1
                continue
            native += t['type'].startswith('native_')
            if t['type']!='tick':
                continue
            ticks+=1
            dropped=max(dropped,t['dropped'])
            assert t['writer_error'] is None, path
            g,ball=t['game'],t['ball']
            if not g or not ball or g['state']!='PLAYING' or g['stopped'] or g['set_play']!='NONE' or g['kicking_team']!=255:
                continue
            carrier=next((p for p in t['players'] if p['role']=='attacker' and p['pose'] is not None),None)
            for p in t['players']:
                if p['id']==1 or p['role']!='support' or p['action'] not in ('support','roamer:support') or p['pose'] is None:
                    continue
                ball_dist.append(math.dist(p['pose'][:2],ball))
                if ball[0]<0:own_ball_dist.append(ball_dist[-1])
                if carrier is not None:
                    carrier_dist.append(math.dist(p['pose'][:2],carrier['pose'][:2]))
                    if math.dist(carrier['pose'][:2],ball)<=1.0:
                        near_carrier_dist.append(carrier_dist[-1])
                target=next((c['args'][0] for c in p['calls'] if c['method']=='move_to_position' and c['args']),None)
                if target is not None:
                    target_dist.append(math.dist(target,ball))
                    if ball[0]<0:own_target_dist.append(target_dist[-1])
    assert ticks and native and dropped==0 and malformed==0, f'incomplete telemetry: {path}'
    return dict(ticks=ticks,native_events=native,dropped=dropped,malformed=malformed,
                support_ball=summary(ball_dist),support_carrier=summary(carrier_dist),
                support_carrier_within_1m_of_ball=summary(near_carrier_dist),
                target_ball=summary(target_dist),own_half_support_ball=summary(own_ball_dist),
                own_half_target_ball=summary(own_target_dist)), ball_dist, carrier_dist, target_dist, near_carrier_dist


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    args=parser.parse_args()
    reports={}
    ball,carrier,target,near_carrier=[],[],[],[]
    for f in sorted(args.results.glob('batch-*/match-*/telemetry.jsonl.gz')):
        report,a,b,c,d=distances(f)
        reports[str(f.relative_to(args.results))]=report
        ball.extend(a);carrier.extend(b);target.extend(c);near_carrier.extend(d)
    assert reports, 'no telemetry files found'
    output=dict(matches=reports,pooled=dict(support_ball=summary(ball),support_carrier=summary(carrier),target_ball=summary(target),
                                         support_carrier_within_1m_of_ball=summary(near_carrier)))
    (args.results/'support-telemetry.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
