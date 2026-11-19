"""Fixed-trajectory counterfactuals, not a simulator or physical save estimator."""
import argparse
import collections
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD
from team.src.keeper_geometry import guard_target
from team.src.param import ARRIVE_DIST
from team.src.tactics import keeper_tracking_target


def segment_gap(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    scale = max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
    return math.dist(point[:2], (start[0] + scale * dx, start[1] + scale * dy))


def rollout(goal, depth, speed, legacy=False):
    samples = goal['trajectory']
    if len(samples) < 2 or samples[0]['players']['1']['pose'] is None:
        return None
    position = tuple(samples[0]['players']['1']['pose'][:2]);direction = 1;crossing = None
    for a, b in zip(samples, samples[1:]):
        dt = b['wall'] - a['wall']
        if dt <= 0:continue
        steps = max(1, math.ceil(dt / .05))
        for j in range(steps):
            before = position
            available = a['phase'] == 'normal' and a['players']['1']['action'] not in ('recovering', 'penalized', 'keeper:clear')
            if available:
                if legacy:
                    target, direction = keeper_tracking_target(FIELD, position, a['ball'], direction, a['velocity'])
                else:
                    target, direction, _ = guard_target(FIELD, position, a['ball'], direction, a['velocity'], depth)
                distance = math.dist(position, target)
                move = 0 if distance < ARRIVE_DIST else min(speed * dt / steps, distance)
                position = tuple(p + (t - p) * move / max(distance, 1e-9) for p, t in zip(position, target))
            elif b['players']['1']['pose'] is not None:
                position = tuple(b['players']['1']['pose'][:2])
            pball = tuple(x + (y - x) * j / steps for x, y in zip(a['ball'], b['ball']))
            nball = tuple(x + (y - x) * (j + 1) / steps for x, y in zip(a['ball'], b['ball']))
            d0, d1 = pball[0] - before[0], nball[0] - position[0]
            if d0 > 0 >= d1:
                f = d0 / (d0 - d1)
                crossing = abs(pball[1] + f * (nball[1] - pball[1]) - before[1] - f * (position[1] - before[1]))
    return crossing


def clearance(goal):
    if not goal['confirmed_preceding_keeper_touch']:return None
    recovered = goal['turnover']['wallTime']
    attempts = [s for s in goal['trajectory'] if s['wall'] <= recovered and s['players']['1']['action'] == 'keeper:clear']
    if not attempts:return dict(kind='no_observed_clear_request', match=goal['match'], goal=goal['event_id'])
    s = attempts[0];ball = s['ball'];opponents = [p for p in s['opponents'].values() if p is not None]
    commands = [c for c in s['players']['1']['commands'] if c['kind']=='kick_body']
    pose=s['players']['1']['pose']
    angles=[c['direction'] + pose[2] for c in commands]
    def direction(target):return math.atan2(target[1]-pose[1],target[0]-pose[0])
    def ray(angle):
        end=(ball[0]+3*math.cos(angle),ball[1]+3*math.sin(angle))
        return min((segment_gap(p, ball, end) for p in opponents), default=99)
    centre = ray(angles[-1]if angles else direction((7.25,0)))
    options = [((-3, y), ray(direction((-3, y)))) for y in (-4, 4)]
    best = max(options, key=lambda item:item[1]);after = [t['ball'] for t in goal['trajectory'] if s['wall'] <= t['wall'] <= recovered]
    return dict(kind='observed_clear_request', match=goal['match'], goal=goal['event_id'], ball=ball, wall=s['wall'],
                requested_field_angles=angles,
                max_forward_progress=max((p[0] - ball[0] for p in after), default=0),
                observed_ball_path=after, centre_first_3m_lane_gap=centre, best_outlet=best,
                estimated_outlet_gain=centre < .45 <= best[1])


def validate_goals(rows, goals):
    csv_keys=collections.Counter(('/'.join((r['version'],r['batch'],r['match'])),round(float(r['sim_time']),3),r['keeper_status'])for r in rows)
    audit_keys=collections.Counter(('/'.join(Path(g['match']).parts[-3:]),round(g['sim_time'],3),g['category'])for g in goals)
    if csv_keys != audit_keys:
        raise ValueError('GOALS.csv and trajectory audit do not describe the same goals')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--audit',type=Path,required=True);parser.add_argument('--goals',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();audit=json.loads(args.audit.read_text());goals=[g for m in audit['matches']for g in m['goals']]
    with args.goals.open(newline='')as source:rows=list(csv.DictReader(source))
    validate_goals(rows,goals)
    results={};details=[]
    speeds=(.05,.1,.15,.2,.25,.5)
    baseline={speed:[rollout(g,.4,speed,legacy=True)for g in goals]for speed in speeds}
    for depth in (.4,.6,.8,1.0,1.2):
        for speed in speeds:
            counts=collections.Counter();rows=[]
            for index,g in enumerate(goals):
                gap=rollout(g,depth,speed);old=g['crossing'];was=old is not None and old['lateral_gap']<=.45
                covered=gap is not None and gap<=.45
                old_model=baseline[speed][index];model_was=old_model is not None and old_model<=.45
                counts['covered']+=covered;counts['newly_covered']+=covered and not was;counts['lost_coverage']+=was and not covered
                counts['legacy_model_covered']+=model_was
                counts['gain_vs_legacy_model']+=covered and not model_was
                counts['loss_vs_legacy_model']+=model_was and not covered
                counts['lateral_misses_newly_covered']+=covered and g['category']=='keeper_lateral_lane_miss'
                rows.append(dict(match=g['match'],goal=g['event_id'],gap=gap,baseline_covered=was,legacy_model_gap=old_model))
            counts['net_coverage_gain']=counts['newly_covered']-counts['lost_coverage']
            counts['net_vs_legacy_model']=counts['gain_vs_legacy_model']-counts['loss_vs_legacy_model']
            key=f'depth-{depth:.1f}_speed-{speed:.2f}';results[key]=dict(counts);details.append(dict(model=key,goals=rows))
    clears=[c for g in goals if (c:=clearance(g))is not None]
    output=dict(position_estimates=results,position_details=details,clearances=clears,
                inputs=dict(goals=len(goals),goals_csv_sha256=hashlib.sha256(args.goals.read_bytes()).hexdigest(),
                            trajectory_audit_sha256=hashlib.sha256(args.audit.read_bytes()).hexdigest()),
                clearance_counts=dict(collections.Counter(c['kind'] for c in clears)),
                outlet_lane_gain=sum(c.get('estimated_outlet_gain',False)for c in clears))
    args.output.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({k:v for k,v in output.items()if k not in('position_details','clearances')},indent=2))
    for c in clears:
        if c['kind']=='observed_clear_request':print(json.dumps(c))


if __name__=='__main__':main()
