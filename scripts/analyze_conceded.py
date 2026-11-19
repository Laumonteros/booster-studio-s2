"""Offline goal-against audit. Proximity origins are not observed physical shots."""
import argparse
import bisect
import collections
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD, GameState, SetPlay
from team.src.param import ANGULAR_GAIN, CONTACT_SLOW_RADIUS_M, CONTACT_SPEED_SCALE, LINEAR_GAIN, MAX_ANGULAR, MAX_LINEAR, TURN_SPEED_REDUCTION
from team.src.tactics import (
    keeper_intercept, keeper_tracking_target, keeper_velocity_update,
    keeper_waypoint, phase,
)


def distance(a,b):
    return None if a is None or b is None else math.dist(a[:2],b[:2])


def nearest(samples,times,wall):
    index=bisect.bisect_right(times,wall)-1
    return samples[index]if samples and index>=0 else None


def crossing(samples):
    found=None
    for a,b in zip(samples,samples[1:]):
        if a['ball']is None or b['ball']is None:continue
        ka,kb=a['players'].get('1'),b['players'].get('1')
        if ka is None or kb is None or ka['pose']is None or kb['pose']is None:continue
        d0=a['ball'][0]-ka['pose'][0];d1=b['ball'][0]-kb['pose'][0]
        if d0>0 and d1<=0 and b['wall']-a['wall']<.2:
            f=d0/(d0-d1);by=a['ball'][1]+f*(b['ball'][1]-a['ball'][1]);ky=ka['pose'][1]+f*(kb['pose'][1]-ka['pose'][1])
            found=dict(wall=a['wall']+f*(b['wall']-a['wall']),ball_y=by,keeper_y=ky,
                       lateral_gap=abs(by-ky),before=a,after=b)
    return found


def contact_limit(players,opponents):
    k=players.get('1')
    if k is None or k['pose']is None or k['walk']is None or k['action']!='keeper:intercept':return None
    pose=k['pose'];others=[p['pose']for i,p in players.items()if i!='1'and p['pose']is not None]
    others +=[p for p in opponents.values()if p is not None]
    if not others:return None
    gap=min(math.dist(pose[:2],p[:2])for p in others)
    yaw=min(MAX_ANGULAR,ANGULAR_GAIN*abs(math.atan2(math.sin(pose[2]),math.cos(pose[2]))))
    nominal=MAX_LINEAR/(1+TURN_SPEED_REDUCTION*yaw)
    cap=nominal*CONTACT_SPEED_SCALE
    requested=LINEAR_GAIN*math.dist(pose[:2],k['walk'])
    commands=[c for c in k['commands']if c['kind']=='velocity_body'and c['accepted']]
    actual=None if not commands else math.hypot(*commands[-1]['velocity'][:2])
    return dict(robot_gap=gap,requested_speed=requested,contact_cap=cap,uncrowded_cap=nominal,actual_speed=actual,
                binding=gap<CONTACT_SLOW_RADIUS_M and requested>cap and actual is not None and .98*cap<=actual<=1.02*cap)


def audit_goal(match,side,events,goal,samples,times):
    before=[e for e in events if e['wallTime']<goal['wallTime']]
    touches=[e for e in before if e['type']=='ball_touch']
    last=touches[-1]if touches else None
    rivals=[e for e in touches if e['actor']['side']!=side]
    turnover=rivals[-1]if rivals else None
    start=nearest(samples,times,turnover['wallTime'])if turnover else None
    previous_reset=next((e for e in reversed(before)if e['type']in('ball_placement_started','goal')),None)
    window=[s for s in samples if goal['wallTime']-12<=s['wall']<=goal['wallTime']and s['ball']is not None and s['fresh']]
    prox=[s for s in window if s['state']=='PLAYING'and not s['stopped']and s['opponent_gap']is not None and s['opponent_gap']<=.65]
    shot=prox[-1]if prox else None
    if shot is None:
        shot=nearest(samples,times,turnover['wallTime'])if turnover else None
    cross=crossing(window)
    final=window[-1]if window else nearest(samples,times,goal['wallTime'])
    keeper=None if final is None else final['players'].get('1')
    kcross=keeper if cross is None else cross['before']['players'].get('1')
    x=None if kcross is None or kcross['pose']is None else kcross['pose'][0]
    advance=any(s['players'].get('1',{}).get('action')=='keeper:clear'for s in window
                if goal['wallTime']-s['wall']<4)
    if kcross is None or kcross['pose']is None:category='keeper_unobserved'
    elif kcross['action']in('recovering','penalized'):category='keeper_unavailable'
    elif x> -5.95 or x< -7.1 or abs(kcross['pose'][1])>1.4:
        category='keeper_advanced_after_clear'if advance else'keeper_out_of_goal_position'
    elif cross is None:category='no_observed_keeper_plane_crossing'
    elif cross['lateral_gap']<=.45:category='goal_through_close_keeper_coverage'
    else:category='keeper_lateral_lane_miss'
    correct=[];limited=[];limited_correct=[]
    if cross is not None:
        correct=[s for s in window if cross['wall']-2<s['wall']<cross['wall']
                 and s['players'].get('1',{}).get('pose')is not None and s['ball'][0]>s['players']['1']['pose'][0]
                 and s['target']is not None and abs(s['target'][1]-cross['ball_y'])<=.3
                 and s['players'].get('1',{}).get('action')=='keeper:intercept']
        limited=[s for s in window if cross['wall']-2<s['wall']<cross['wall']and s['contact_limit']is not None and s['contact_limit']['binding']]
        limited_correct=[s for s in correct if s['contact_limit']is not None and s['contact_limit']['binding']]
    own_final=last is not None and last['actor']['side']==side
    previous_key=None if turnover is None else turnover.get('outcome',{}).get('previousTouchRobotKey')
    keeper_touch=previous_key==side+':1'
    if keeper_touch:origin='after_recorded_keeper_contact'
    elif previous_reset is not None and (turnover is None or turnover['wallTime']<=previous_reset['wallTime']):origin='restart_without_recorded_turnover'
    elif turnover is not None and turnover.get('outcome',{}).get('setPlay')not in(None,'noSetPlay'):origin='restart_touch'
    elif start is None or start['ball']is None:origin='unknown'
    elif start['ball'][0]<-3:origin='turnover_defensive_third'
    elif start['ball'][0]<3:origin='turnover_middle_third'
    else:origin='turnover_attacking_third'
    ball=None if shot is None else shot['ball']
    return dict(match=str(match),event_id=goal['eventId'],wall=goal['wallTime'],sim_time=goal['simTime'],
                score=goal['score'],category=category,attack_origin=origin,
                turnover=turnover,turnover_snapshot=start,previous_reset=previous_reset,
                shot_origin_proxy=shot,shot_distance=None if ball is None else math.dist(ball,(-7,0)),
                shot_angle_degrees=None if ball is None else math.degrees(math.atan2(abs(ball[1]),ball[0]+7)),
                crossing=cross,final=final,keeper_clear_in_last_four_wall_s=advance,
                correct_intercept_lead_wall_s=None if not correct else cross['wall']-correct[0]['wall'],
                first_correct_intercept=None if not correct else correct[0],
                contact_binding_samples=len(limited),contact_binding_correct_target_samples=len(limited_correct),
                binding_example=None if not limited_correct else limited_correct[0],
                recorded_final_touch_own_side=own_final,recorded_final_touch=last,
                confirmed_preceding_keeper_touch=keeper_touch,
                trajectory=window[::6])


def analyze(match):
    events=list(map(json.loads,(match/'events.jsonl').read_text().splitlines()))
    side=json.loads((match/'summary.json').read_text())['side']
    goals=[e for e in events if e['type']=='goal'and e['actor']['side']!=side]
    assert len(goals)==json.loads((match/'summary.json').read_text())['goals_against']
    provenance=json.loads((match.parent/'provenance.json').read_text())
    for name in('src/tactics.py','src/param.py','src/main.py'):
        assert hashlib.sha256((Path(__file__).parents[1]/'team'/name).read_bytes()).hexdigest()==provenance['team_source_sha256'][name]
    samples=[];motion=None;direction=1;counts=collections.Counter()
    with gzip.open(match/'telemetry.jsonl.gz','rt')as f:
        for t in map(json.loads,f):
            if t['type']!='tick':continue
            assert t['dropped']==0 and t['writer_error']is None
            g=t['game'];ball=t['ball'];counts['ticks']+=1
            game=None if g is None else SimpleNamespace(state=GameState[g['state']],stopped=g['stopped'],
                    set_play=SetPlay[g['set_play']],kicking_team=g['kicking_team'],secondary_time=g['secondary'])
            current=phase(SimpleNamespace(game=game,team_id=t['team']))
            motion=keeper_velocity_update(motion,None if ball is None else tuple(ball),t['now']if ball is None else t['ball_seen'],t['now'],current)
            velocity=None if motion is None else motion[2]
            players={str(p['id']):dict(pose=p['pose'],action=p['action'],native=p['native_active'],
                        commands=p['commands'],walk=next((c['args'][0]for c in p['calls']if c['method']=='walk_to'),None))for p in t['players']}
            k=players.get('1');target=None
            if k is not None and k['pose']is not None and k['action']in('keeper:track','keeper:intercept'):
                target,direction=keeper_tracking_target(FIELD,k['pose'][:2],ball,direction,velocity)
                expected=keeper_waypoint(k['pose'][:2],target)
                counts['keeper_walk_replay']+=1
                if k['walk']is not None and math.dist(expected,k['walk'])<1e-7:counts['keeper_walk_match']+=1
            opponents=[p for p in t['opponents'].values()if p is not None]
            limiter=contact_limit(players,t['opponents'])
            if limiter is not None and limiter['binding']:
                counts['contact_binding_intercept_samples']+=1
                if all(abs(t['wall']-g['wallTime'])>4 for g in goals):counts['contact_binding_outside_conceded_goal_windows']+=1
            samples.append(dict(wall=t['wall'],ball=ball,fresh=ball is not None and t['now']-t['ball_seen']<=.15,
                    state=None if g is None else g['state'],stopped=g is None or g['stopped'],phase=current,
                    players=players,opponents=t['opponents'],velocity=velocity,target=target,contact_limit=limiter,
                    opponent_gap=None if ball is None or not opponents else min(math.dist(ball,p[:2])for p in opponents)))
    times=[s['wall']for s in samples]
    return dict(match=str(match),replay=dict(counts),goals=[audit_goal(match,side,events,g,samples,times)for g in goals])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('results',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();reports=[]
    for root in args.results:
        for path in sorted(root.glob('batch-*/match-*/result.json')):
            report=analyze(path.parent);reports.append(report)
    goals=[g for m in reports for g in m['goals']]
    counts=collections.Counter(g['category']for g in goals);origins=collections.Counter(g['attack_origin']for g in goals)
    replay=collections.Counter()
    for m in reports:replay.update(m['replay'])
    out=dict(goals=len(goals),categories=dict(counts),origins=dict(origins),replay=dict(replay),matches=reports)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items()if k!='matches'},indent=2))
    for g in goals:
        print(Path(g['match']).parents[1].name,Path(g['match']).parent.name,Path(g['match']).name,round(g['sim_time'],1),
              g['category'],g['attack_origin'],'range',None if g['shot_distance']is None else round(g['shot_distance'],2),
              'gap',None if g['crossing']is None else round(g['crossing']['lateral_gap'],2),
              'lead',None if g['correct_intercept_lead_wall_s']is None else round(g['correct_intercept_lead_wall_s'],2),
              'ownfinal',g['recorded_final_touch_own_side'])


if __name__=='__main__':main()
