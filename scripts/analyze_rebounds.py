"""Loose-ball distance races, not predictions of physical arrival times."""
import argparse
import collections
import gzip
import json
import math
import statistics
from pathlib import Path


def normal(tick):
    g = tick['game']
    return (g is not None and g['state']=='PLAYING' and not g['stopped']
            and g['set_play']=='NONE' and g['kicking_team']==255 and g['secondary']==0)


def flank(ball, support):
    dx, dy = 7-ball[0], -ball[1]
    length = max(math.hypot(dx,dy),1e-6)
    ux, uy = dx/length, dy/length
    side = 1 if (support[0]-ball[0])*(-uy)+(support[1]-ball[1])*ux>=0 else -1
    along = .8-2.3*max(0.,min(1.,ball[0]/2))
    return [max(-6.25,min(6.25,ball[0]-along*ux-side*1.25*uy)),
            max(-3.75,min(3.75,ball[1]-along*uy+side*1.25*ux))]


def intercept(path, positions, speed):
    return next((dt for dt,x,y in path if min(math.dist(p[:2],(x,y))for p in positions)<=.65+speed*dt),math.inf)


def analyze(match):
    counts=collections.Counter();windows=[];close=recent=contact=None;flight=None
    with gzip.open(match/'telemetry.jsonl.gz','rt')as f:
        for t in map(json.loads,f):
            if t['type']!='tick':continue
            assert t['dropped']==0 and t['writer_error'] is None
            if not normal(t)or t['ball']is None or t['now']-t['ball_seen']>.15:
                close=recent=contact=flight=None
                continue
            b=t['ball'];players=[p for p in t['players']if p['pose']is not None]
            opponents=[p for p in t['opponents'].values()if p is not None]
            if not players or not opponents:continue
            distances=[(math.dist(b[:2],p['pose'][:2]),'own',p['id'])for p in players]
            distances += [(math.dist(b[:2],p[:2]),'opponent',i)for i,p in enumerate(opponents)]
            distances.sort()
            if (distances[0][1]=='opponent' and distances[0][0]<=.65 and recent is not None
                    and recent['goal_zone'] and t['wall']-recent['wall']<=3):
                contact=dict(wall=t['wall'],support=recent['support'],goal_zone=True)
            if flight is not None:
                flight['path'].append([t['wall']-flight['wall'],*b[:2]])
                if t['wall']-flight['wall']>2 or math.dist(b[:2],flight['ball'][:2])>3:
                    counts['censored_flights']+=1;flight=close=None
                elif distances[0][0]<=.65:
                    if len(distances)>1 and distances[1][0]-distances[0][0]<.15:
                        counts['ambiguous_recoveries']+=1;flight=close=None;continue
                    point=b[:2];support=flight['support'];opponents0=flight['opponents']
                    actual=math.dist(support['pose'][:2],point)
                    opponent=min(math.dist(p[:2],point)for p in opponents0)
                    target=flank(flight['ball'],support['pose']);counterfactual=math.dist(target,point)
                    _,team,robot=distances[0]
                    winner='opponent'if team=='opponent'else('support'if robot==support['id']else'other_own')
                    counts['loose_windows']+=1;counts['next_proximity_'+winner]+=1
                    counts['support_distance_advantage']+=actual+.3<opponent
                    counts['opponent_distance_advantage']+=opponent+.3<actual
                    counts['flank_preposition_distance_advantage']+=counterfactual+.3<opponent
                    counts['opponent_won_flank_would_lead']+=winner=='opponent'and actual>=opponent and counterfactual+.3<opponent
                    counts['attacking_half_windows']+=flight['ball'][0]>=0
                    counts['goal_zone_requests']+=flight['goal_zone']
                    counts[flight['kind']]+=1
                    for speed in (.75,1.,1.5):
                        old=intercept(flight['path'],[support['pose']],speed)
                        new=intercept(flight['path'],[target],speed)
                        rival=intercept(flight['path'],opponents0,speed)
                        counts[f'model_{speed}_actual_support_first']+=old+.1<rival
                        counts[f'model_{speed}_flank_first']+=new+.1<rival
                        counts[f'model_{speed}_lost_race_flank_first']+=winner=='opponent'and old>=rival and new+.1<rival
                    windows.append(dict(wall=flight['wall'],ball=flight['ball'],point=point,support=support['pose'],
                                        support_gap=actual,opponent_gap=opponent,flank_target=target,flank_gap=counterfactual,
                                        winner=winner,goal_zone=flight['goal_zone'],kind=flight['kind'],path=flight['path'][::3],
                                        ball_support_gap=math.dist(flight['ball'][:2],support['pose'][:2])))
                    flight=close=None
                continue
            attacker=next((p for p in players if p['id']!=1 and p['action']=='attack'
                           and math.dist(b[:2],p['pose'][:2])<=.65
                           and any(c['kind']=='kick_body'for c in p['commands'])),None)
            support=next((p for p in players if p['id']!=1 and p['action'].startswith('support')),None)
            if attacker is not None and support is not None:
                close=dict(wall=t['wall'],goal_zone=math.dist(b[:2],(7,0))<=4.5,support=support['id'])
                recent=close
            own=close is not None and t['wall']-close['wall']<=.5
            rebound=(contact is not None and recent is not None and t['wall']-contact['wall']<=.5
                     and t['wall']-recent['wall']<=3)
            if (own or rebound)and distances[0][0]>.9:
                trigger=close if own else contact
                partner=next((p for p in players if p['id']==trigger['support']),None)
                if partner is not None:
                    flight=dict(wall=t['wall'],ball=b,support=partner,opponents=opponents,
                                goal_zone=trigger['goal_zone'],kind='after_own_request'if own else'after_opponent_proximity',path=[])
                    contact=None
    return dict(match=str(match),counts=dict(counts),windows=windows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('results',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();reports=[];counts=collections.Counter()
    for root in args.results:
        for path in sorted(root.glob('batch-*/match-*/telemetry.jsonl.gz')):
            if (path.parent/'failure.json').exists():
                continue
            report=analyze(path.parent);reports.append(report);counts.update(report['counts'])
    windows=[w for r in reports for w in r['windows']]
    medians={key:statistics.median(w[key]for w in windows)if windows else None
             for key in('support_gap','opponent_gap','flank_gap','ball_support_gap')}
    out=dict(totals=dict(counts),medians=medians,matches=reports)
    args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(totals=dict(counts),medians=medians),indent=2))


if __name__=='__main__':main()
