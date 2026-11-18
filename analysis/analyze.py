import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from config import RAW, OUT, records, targets

PID='8b44c8b4-aa9d-4511-8513-1a1ef4f6114e'
def record(r):
    side='home' if (r.get('home_team') or {}).get('player_id')==PID else 'away'
    other='away' if side=='home' else 'home'
    p=r['perspective'];result=r.get('result') or {}
    return dict(id=r['id'],date=r['scheduled_at'],source=r['source'],stage=(r.get('stage') or {}).get('type','arena'),side=side,opponent=(r.get(other+'_team') or {}).get('name','unknown'),opponent_id=(r.get(other+'_team') or {}).get('player_id','unknown'),outcome=p['outcome'],gf=p['score_for'],ga=p['score_against'],fouls=result.get(side+'_fouls'),opponent_fouls=result.get(other+'_fouls'))

def aggregate(g):
    return pd.Series(dict(N=len(g),W=(g.outcome=='win').sum(),D=(g.outcome=='draw').sum(),L=(g.outcome=='loss').sum(),GF=g.gf.sum(),GA=g.ga.sum(),GF_game=g.gf.mean(),GA_game=g.ga.mean(),clean_sheets=(g.ga==0).sum(),fouls=g.fouls.sum(),fouls_game=g.fouls.mean(),opp_fouls_game=g.opponent_fouls.mean()))

def main():
    ALL=records();TARGET=targets(ALL)
    OUT.mkdir(parents=True, exist_ok=True)
    rec=pd.DataFrame([record(r) for r in ALL if r.get('perspective')]);rec.to_csv(OUT/'records.csv',index=False)
    groups={'All':rec,'OFFICIAL S1':rec[rec.source=='OFFICIAL'],'Arena':rec[rec.source=='FREE_BATTLE']}
    for stage,g in rec[rec.source=='OFFICIAL'].groupby('stage'):groups['S1 '+stage]=g
    for n in [10,20,50]:groups['Arena recent '+str(n)]=rec[rec.source=='FREE_BATTLE'].sort_values('date',ascending=False).head(n)
    pd.DataFrame({k:aggregate(v) for k,v in groups.items()}).T.to_csv(OUT/'record_summary.csv')
    rec.groupby(['source','opponent_id','opponent'],dropna=False).apply(aggregate,include_groups=False).to_csv(OUT/'opponents.csv')
    robotrows=[];teamrows=[];goalrows=[];trajectoryrows=[];foulrows=[];coverage=[]
    heats={}
    for r in TARGET:
        row=record(r);folder=RAW/r['id'];legacy=(folder/'legacy_samples.json').exists()
        if legacy:
            frames=json.loads((folder/'legacy_samples.json').read_text());m=json.loads((folder/'legacy_result.json').read_text());events=[json.loads(l) for l in (folder/'legacy_events.jsonl').read_text().splitlines()];duration=json.loads((folder/'legacy_manifest.json').read_text())['durationSeconds']
        elif (folder/'manifest.json').exists():
            manifest=json.loads((folder/'manifest.json').read_text());m=manifest['match'];events=manifest['events'];duration=manifest['durationSeconds'];frames=[]
            for seg in manifest['segments']:
                p=folder/('sample_'+str(seg['index'])+'.json')
                if not p.exists():raise FileNotFoundError(f'Missing segment {p}; run fetch.py first')
                frames+=json.loads(p.read_text())
        else:coverage.append(dict(id=r['id'],available=False));continue
        events=sorted([e for e in events if e.get('simTime') is not None],key=lambda e:e['simTime'])
        frames=sorted({round(f['time'],5):f for f in frames}.values(),key=lambda f:f['time'])
        t=np.array([f['time'] for f in frames]);ball=np.array([f['ball']['position'][:2] for f in frames]);finish=next((e for e in reversed(events) if e['type']=='match_finished'),events[-1]);offset=finish['simTime']-duration
        # Use event state transitions when old frames have no command-intent game state.
        et=np.array([e['simTime']-offset for e in events]);ei=np.clip(np.searchsorted(et,t,side='right')-1,0,len(events)-1)
        games=[(f.get('commandIntents') or {}).get('game') or events[j].get('game',{}) for f,j in zip(frames,ei)]
        playing=np.array([g.get('state')=='playing' for g in games]);base_sign=np.array([-1 if g.get('sides')=='homeDefendsRightGoal' else 1 for g in games]);sign=base_sign*(1 if row['side']=='home' else -1)
        coverage.append(dict(id=r['id'],available=True,format='legacy ZIP' if legacy else 'segments',frames=len(frames),playing_frames=int(playing.sum()),duration=duration,offset=offset,goal_events=sum(e['type']=='goal' for e in events),expected_goals=row['gf']+row['ga']))
        positions={};distances={}
        for side in ['home','away']:
            positions[side]=np.array([[sorted([a for a in f['robots'] if a['side']==side],key=lambda a:a['playerNumber'])[k]['basePosition'][:2] for k in range(3)] for f in frames])
            distances[side]=np.linalg.norm(positions[side]-ball[:,None,:],axis=2)
        for side in ['home','away']:
            label='champion' if side==row['side'] else 'opponent';other='away' if side=='home' else 'home';ss=base_sign*(1 if side=='home' else -1);xy=positions[side]*ss[:,None,None];b=ball*ss[:,None];d=distances[side];mask=playing
            stats=m['teams'][side]['stats'];fouls=stats.get('fouls',{})
            for reason,count in fouls.get('byReason',{}).items():foulrows.append(dict(id=r['id'],source=r['source'],team=label,reason=reason,count=count))
            closest=d.argmin(axis=1)
            for k in range(3):
                rob=[sorted([a for a in f['robots'] if a['side']==side],key=lambda a:a['playerNumber'])[k] for f in frames];up=np.array([a.get('upDot',1) for a in rob]);fallen=up<.45;step=np.linalg.norm(np.diff(positions[side][:,k,:],axis=0),axis=1);dt=np.diff(t)
                valid=mask[1:]&mask[:-1]&(dt<1)&(step/np.maximum(dt,.001)<4)
                x=xy[:,k,0];y=xy[:,k,1]
                robotrows.append(dict(id=r['id'],source=r['source'],outcome=row['outcome'],team=label,player=k+1,mean_x=x[mask].mean(),std_x=x[mask].std(),mean_y=y[mask].mean(),std_y=y[mask].std(),own_half=(x[mask]<0).mean()*100,own_box=((x[mask]<=-5)&(abs(y[mask])<=2.5)).mean()*100,goal_distance=np.linalg.norm(xy[:,k,:]-np.array([-7,0]),axis=1)[mask].mean(),ball_distance=d[mask,k].mean(),closest=(closest[mask]==k).mean()*100,distance=step[valid].sum(),excluded_steps=int((mask[1:]&mask[:-1]&~valid).sum()),fallen_pct=fallen[mask].mean()*100,fall_episodes=int((fallen[1:]&~fallen[:-1]&mask[1:]).sum()),fouls=fouls.get('byRobot',{}).get(rob[0]['name'],0)))
                heats.setdefault((r['source'],label,k),[]).append(xy[mask,k,:])
            pair=np.mean([np.linalg.norm(xy[:,a,:]-xy[:,b,:],axis=1) for a,b in [(0,1),(0,2),(1,2)]],axis=0)
            teamrows.append(dict(id=r['id'],source=r['source'],outcome=row['outcome'],team=label,playing_frames=mask.sum(),line_height=xy[:,:,0].mean(axis=1)[mask].mean(),deepest_x=xy[:,:,0].min(axis=1)[mask].mean(),width=np.ptp(xy[:,:,1],axis=1)[mask].mean(),depth=np.ptp(xy[:,:,0],axis=1)[mask].mean(),spread=pair[mask].mean(),closest_proxy=(d.min(axis=1)[mask]<distances[other].min(axis=1)[mask]).mean()*100,ball_mean_x=b[mask,0].mean(),ball_own_half=(b[mask,0]<0).mean()*100,ball_attack_third=(b[mask,0]>7/3).mean()*100,ball_defense_third=(b[mask,0]<-7/3).mean()*100))
            heats.setdefault((r['source'],label,'ball'),[]).append(b[mask])
        for event in events:
            if event['type']!='goal':continue
            gt=event['simTime']-offset;ix=np.where((t>=gt-5)&(t<gt))[0]
            if not len(ix):continue
            sg=sign[ix[-1]];b=ball[ix]*sg
            near=[]
            for j in ix:
                for side in ['home','away']:
                    k=distances[side][j].argmin();dd=distances[side][j,k]
                    if dd<.65:near.append((t[j],dd,side,k+1))
            near.sort(key=lambda v:(v[0],-v[1]));last=near[-1] if near else None
            touches=[e for e in events if e['type']=='ball_touch' and gt-5<=e['simTime']-offset<=gt]
            touch=touches[-1].get('actor') if touches else None
            scored=(event.get('actor') or {}).get('side')==row['side'];elapsed=600-event.get('timing',{}).get('timeRemaining',600)
            goalrows.append(dict(id=r['id'],source=r['source'],outcome=row['outcome'],kind='scored' if scored else 'conceded',time=gt,clock_elapsed=elapsed,start_x=b[0,0],start_y=b[0,1],end_x=b[-1,0],end_y=b[-1,1],window_seconds=t[ix[-1]]-t[ix[0]],last_near_team=('champion' if last[2]==row['side'] else 'opponent') if last else None,last_near_player=last[3] if last else None,last_touch_team=('champion' if touch['side']==row['side'] else 'opponent') if touch else None,last_touch_player=touch.get('playerNumber') if touch else None))
            for j in ix:trajectoryrows.append(dict(id=r['id'],event_id=event['eventId'],kind='scored' if scored else 'conceded',seconds_before_goal=t[j]-gt,x=ball[j,0]*sg,y=ball[j,1]*sg))
    robots=pd.DataFrame(robotrows)
    if robots.empty:
        pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
        raise ValueError('No usable replay frames; run fetch.py first')
    robots['role']='roamer'
    for _,indices in robots.groupby(['id','team']).groups.items():
        deepest=robots.loc[indices,'mean_x'].idxmin();robots.loc[deepest,'role']='deepest/keeper'
    robots.to_csv(OUT/'robots.csv',index=False)
    for name,rows in [('teams',teamrows),('goals',goalrows),('goal_trajectories',trajectoryrows),('fouls_by_reason',foulrows),('coverage',coverage)]:pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)
    for source in ['OFFICIAL','FREE_BATTLE']:
        if (source,'champion',0) not in heats:continue
        fig,axes=plt.subplots(1,3,figsize=(15,4),constrained_layout=True)
        role_data={'deepest/keeper':[],'roamer':[]}
        # Match order in heat arrays follows TARGET, as does the per-match role assignment.
        matches=[r for r in TARGET if r['source']==source and (robots.id==r['id']).any()]
        for k in range(3):
            for match,data in zip(matches,heats[(source,'champion',k)]):
                role=robots[(robots.id==match['id'])&(robots.team=='champion')&(robots.player==k+1)].iloc[0]['role'];role_data[role].append(data)
        for ax,(title,data) in zip(axes,[('Deepest / keeper',np.concatenate(role_data['deepest/keeper'])),('Two roamers',np.concatenate(role_data['roamer'])),('All three',np.concatenate([np.concatenate(heats[(source,'champion',k)]) for k in range(3)]))]):plot_heat(ax,data,title)
        fig.suptitle('Yueyue: '+source+' | playing-state positions, attacks +x')
        fig.savefig(OUT/('robots_'+source+'.png'),dpi=160);plt.close(fig)
    sources=[s for s in ['OFFICIAL','FREE_BATTLE'] if (s,'champion','ball') in heats]
    fig,axes=plt.subplots(1,len(sources),figsize=(5.5*len(sources),4),constrained_layout=True,squeeze=False)
    for source,ax in zip(sources,axes[0]):plot_heat(ax,np.concatenate(heats[(source,'champion','ball')]),source+' ball')
    fig.savefig(OUT/'ball_heatmaps.png',dpi=160);plt.close(fig)
    teams=pd.DataFrame(teamrows)
    robots.groupby(['source','team','player']).mean(numeric_only=True).to_csv(OUT/'robot_summary.csv')
    robots.groupby(['source','team','role']).mean(numeric_only=True).to_csv(OUT/'role_summary.csv')
    teams.groupby(['source','team','outcome']).mean(numeric_only=True).to_csv(OUT/'team_summary.csv')
    print('ANALYSIS OK:',len(rec),'records;',len(coverage),'replays;',len(robotrows),'robot-match rows;',len(goalrows),'goals')

def plot_heat(ax,data,title):
    ax.hist2d(data[:,0],data[:,1],bins=[56,36],range=[[-7,7],[-4.5,4.5]],cmap='magma',density=True)
    ax.plot([-7,7,7,-7,-7],[-4.5,-4.5,4.5,4.5,-4.5],color='white',lw=1);ax.axvline(0,color='white',lw=.6)
    for sign in [-1,1]:ax.plot([sign*7,sign*5,sign*5,sign*7],[-2.5,-2.5,2.5,2.5],color='white',lw=.5)
    ax.set(title=title,xlabel='x (m); attack →',ylabel='y (m)',aspect='equal')

if __name__=='__main__':main()
