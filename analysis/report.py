import pandas as pd
from config import OUT, records, targets

def table(df):
    df=df.copy().reset_index(drop=True)
    def fmt(v):
        if isinstance(v,float):return f'{v:.2f}'
        return str(v)
    return '\n'.join(['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']+['| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None)])

def main():
    if len(records())!=371 or len(targets(records()))!=41:
        raise ValueError('Narrative is curated for the committed 371-record/41-target snapshot; do not regenerate it from partial or updated data')
    summary=pd.read_csv(OUT/'record_summary.csv').rename(columns={'Unnamed: 0':'Scope'})
    robots=pd.read_csv(OUT/'robot_summary.csv');roles=pd.read_csv(OUT/'role_summary.csv');teams=pd.read_csv(OUT/'teams.csv');goals=pd.read_csv(OUT/'goals.csv');rec=pd.read_csv(OUT/'records.csv');opp=pd.read_csv(OUT/'opponents.csv')
    goals['bin']=pd.cut(goals.clock_elapsed,[-1,120,240,360,480,10000],labels=['0–2','2–4','4–6','6–8','8+'])
    timing=goals.groupby(['source','kind','bin'],observed=True).size().unstack(fill_value=0).reset_index()
    starts=goals.groupby(['source','kind']).agg(N=('time','size'),start_x=('start_x','mean'),abs_start_y=('start_y',lambda x:x.abs().mean()),own_half_starts=('start_x',lambda x:(x<0).sum()),central_starts=('start_y',lambda x:(x.abs()<1.5).sum())).reset_index()
    official=opp[opp.source=='OFFICIAL'][['opponent','N','W','D','L','GF','GA']]
    arena=opp[opp.source=='FREE_BATTLE'].sort_values('N',ascending=False).head(10)[['opponent','N','W','D','L','GF','GA']]
    role_cols=['source','team','role','mean_x','mean_y','own_half','own_box','goal_distance','ball_distance','closest','distance','fallen_pct','fouls']
    robot_cols=['source','player','mean_x','std_x','mean_y','std_y','own_half','own_box','goal_distance','ball_distance','closest','distance','fallen_pct','fouls']
    shape=teams.groupby(['source','team'])[['line_height','width','depth','spread','closest_proxy','ball_mean_x','ball_own_half','ball_attack_third','ball_defense_third']].mean().reset_index()
    comparison=teams[teams.team=='champion'].groupby(['source','outcome']).agg(N=('id','size'),line_x=('line_height','mean'),width=('width','mean'),spread=('spread','mean'),closest_pct=('closest_proxy','mean'),ball_x=('ball_mean_x','mean'),ball_def_third_pct=('ball_defense_third','mean')).reset_index()
    text=f'''# How 月月 plays and wins — Booster Studio 3v3 S1

## Executive finding

**The repeatable structure is a very deep goalkeeper plus two mobile field robots—not three equal ball-chasers.** In the 20 available S1 replays, the deepest robot averages x=−6.05 m, spends 89.94% of playing samples in the operational own-box region and moves only 46 m/game versus 187 m for each roamer. In the latest 20 arena matches, the structure is even clearer: goalkeeper x=−6.63 m, 97.27% in-box, 34 m/game. The keeper number is **not fixed throughout S1** (players 1/2/3: 9/5/6 matches); recent arena keeper is #3 in 17/20, #2 in two, #1 in one. Do not infer roles from global player-number averages alone.

The champion won all seven group/knockout games while conceding in every one: 37–21 aggregate. This is successful **outscoring with deep insurance**, not an impenetrable clean-sheet machine. Robot coordinates and proximity do not prove passing intent or shooting quality.

## 1. Match record

Input snapshot: 371 unique match records, scheduled 2026-07-19 through 2026-11-18 (UTC). One failed arena start (`52229bc2-4e1a-46a7-ae8c-63d4a214b66e`, no perspective/result) is excluded: **370 completed results**. Arena means `FREE_BATTLE`, not tournament practice inferred from names. Recent means latest scheduled timestamps, not list position.

{table(summary[['Scope','N','W','D','L','GF','GA','GF_game','GA_game','clean_sheets','fouls_game','opp_fouls_game']])}

All completed-game win rate 79.46%; S1 76.19%; arena 79.66%. Recent 20 arena: 70%, down from the lifetime arena rate, but goals conceded/game are also lower. Different opponents and July-versus-November builds prevent causal claims about improvement.

### S1 opponents (all)
{table(official)}

S1 losses: AI 3–5 (qualification), CNU_lynx 2–3, SUI 0–3, 轻轻敲醒沉睡的心灵 2–3. All four loss replays are available. Final listed knockout win: MIracle 5–2; other knockout wins: hjy 3–2, 王 9–3, 响响 6–5.

### Arena: ten most frequent opponents
{table(arena)}

Robonaldo(Mike) is a genuine adverse head-to-head (3–4–9, 85–96), unlike the heavily farmed unbeaten opponents. Full opponent/player-ID splits, including all opponents beaten or lost to, are in `opponents.csv`; name collisions are not merged across player IDs.

## 2. Robot roles and physical behavior

Positions/distances in metres; percentages 0–100; distance is sampled horizontal travel per match. Entries are equal-match means over playing-state samples, not a pooled 40-match time average. `closest` is share of time closest **among that team's three robots**. `own_box` is x≤−5 and |y|≤2.5 (an explicitly operational region, not independently verified official penalty-box geometry). Own goal reference is (−7,0). Both teams are normalized to their **own** attack +x; this is a 180° rotation, including y.

### Per player number, champion
{table(robots[robots.team=='champion'][robot_cols])}

`std_x/std_y` are mean within-match positional standard deviations, not between-match spread. Because keepers change number, the following role-aligned comparison is the tactical baseline; role is assigned to the deepest mean-x robot in each match, with the other two called roamers. This classification always selects one deepest player, so its existence alone does not demonstrate a fixed goalkeeper: **17/20 S1 deepest players have >85% box occupancy**, versus all 20 recent arena keepers (>92%). The early two qualification matches and one Swiss match are less cleanly separated. Roamers have similar ball-nearness shares (~43% each); no stable, number-specific striker/support hierarchy is established.

### Role-aligned champion and opponent baseline
{table(roles[role_cols])}

Opponent 'keeper' means deepest player even when that opponent has no dedicated keeper. S1 opponent deepest players spend only 72.74% in-box; recent arena opponents 60.83%, compared with 月月 89.94%/97.27%. The champion's roamers are nearer the ball than S1 opponent roamers (3.84 vs 4.37 m), but recent arena roamers average 4.42 vs 4.70 m.

Falls: `upDot<0.45`; episodes are sampled upright→fallen transitions during play, not authoritative referee falls. S1: champion 39 episodes versus opponents 37; recent arena 52 versus 45. Low-upDot sample shares and referee foul counts are separate measurements. Of 月月's S1 33 fouls, 16 were `fallenRobot`, 6 `illegalPosition`, 5 `inactiveRobot`, 5 defender set-play interference, 1 `stopped_motion`. Recent arena 63: 53 fallen, 6 set-play interference, 4 illegal position. Thus **fall/recovery discipline is the strongest current exploit opportunity**, not evidence of deliberate physical fouling. Full opponent and player-number metrics: `robots.csv`, `robot_summary.csv`, `fouls_by_reason.csv`.

## 3. Shape, territory and proximity possession

Line height = mean x of all three; width/depth = max-minus-min y/x; spread = mean pairwise teammate distance. Ball thirds use x=±7/3. Values below use each team's own attacking orientation. Exact center-line samples belong to neither half, so opposing own-half percentages need not sum to 100.

{table(shape)}

S1 has a deeper champion line (−3.03 vs −2.66 m), similar width, and greater depth: consistent with one robot held far behind two roamers. Ball territory is not dominant: 35.84% in the champion defensive third vs 27.21% attacking third. Recent arena is more attack-tilted (37.87% attacking-third vs 30.06% defensive-third), with a more spread-out longitudinal shape.

Possession proxy = which team's nearest robot is nearer to the ball. It is **not controlled possession**: a goalmouth defender can win this proxy while under attack. S1 champion 53.14%, arena 46.57%; the champion can win without winning proximity time.

### Winning versus losing (outcomes always from 月月's perspective)
{table(comparison)}

S1 win/loss shape differences are small (15 available wins vs four losses); no reliable causal formation adjustment follows. Arena wins put the ball much farther forward (+0.82 vs −0.69 m) and reduce defensive-third exposure (26.82% vs 39.43%). Yet losses have *higher* proximity share (55.23 vs 44.43%), a direct warning not to optimize the proxy as possession. Draws are included for completeness; only one S1 and two arena draws.

## 4. Goals: timing and the preceding five seconds

20 S1 replay scorelines reconcile to **77 scored/51 conceded** (the unavailable 3–0 win accounts for the missing three scored goals). Arena: 54/21. Replay goal events match every available match's total score.

Goals by match-clock elapsed minutes (8+ includes any extra time; this is not replay wall time):
{table(timing)}

No obvious S1 late-goal surge: scored distribution 13/16/19/17/12, conceded 9/10/13/10/9. Recent arena scoring is stronger after minute 6 (28/54), but this is descriptive, not evidence of stamina adaptation.

Five-second ball-trajectory starts, champion attack +x; central = |y|<1.5 m:
{table(starts)}

S1 scoring starts close to midfield on average, with 52/77 central-lane starts and 17/77 starting in its own half. S1 concessions begin at mean x=−2.61; recent concessions −2.98. Recent scoring starts farther forward (+1.68). These are **five-second windows**, not shot origins or complete attacks. `goals.csv` records start/end x,y and last nearby robot; `goal_trajectories.csv` preserves each sampled x,y point. Last-near uses any robot within 0.65 m in the window, latest time then closest distance. It is not a scorer/assist label: many scoring windows end with an opposing keeper nearby. S1 scored windows: last-near champion/opponent/missing = 37/37/3; arena scored 19/35/0. Latest logged `ball_touch` actor, when present in the window, is separately recorded.

## Implications for our strategy: 1 goalkeeper + 2 roaming attackers

1. **Keep our goalkeeper genuinely deep and centrally disciplined.** Benchmark x≈−6 to −6.6, >90% in the operational box, not necessarily a hard target; avoid blindly following the ball out. Their persistent keeper means we should expect rebounds and a second save, not an empty net.
2. **Use two coordinated roamers, not a permanently numbered striker/support.** Choose the challenger dynamically; the other provides a lateral/second-ball option and transition cover. 月月's role structure is stable but the assigned number is not. These are recommended responses, not measured proof that 月月 passes in combinations.
3. **Attack in two actions.** Seek a wide approach/cutback or second-ball finish to displace a deep central keeper, rather than merely crowding the nearest-ball contest. Test this against a baseline; trajectories here do not establish a wide-shot success rate.
4. **Protect the central recovery lane.** Most S1 five-second scoring windows begin centrally; keep the non-chasing roamer between ball and our goal until possession is secure. Arena loss territory is a better alarm than proximity share: track defensive-third exposure and shots/concessions, not only who is closest.
5. **Exploit falls safely and fix our own recovery first.** Recent 月月 fallen-robot fouls are 53/63, almost all on roamers (61/63 total fouls on roamers). Capitalize on temporary numerical advantages with a second runner; prevent our keeper wandering during that pressure. Avoid illegal set-play proximity ourselves.
6. **Benchmark on hard opponents.** Use Robonaldo(Mike) and the available SUI loss as stress tests; broad arena win rate is inflated by repeat easy matchups. Current evidence supports the formation, not a guarantee that mirroring it beats the champion.

## Coverage, methods and limitations

- Requested 21 S1 + latest 20 arena (2026-11-17 08:53:08 through 2026-11-18 16:57:20 UTC). **40/41 available: all 20 arena and 20/21 S1.** Missing: `75d85417-6c32-4f56-87cd-74987577891f`, 2026-07-21 06:51:22 UTC vs 新手小白勇闯足球, 3–0 win; detail reports replay `match_state=failed`, `available=false`, `zip_ready=false`, `download_url=null`. The SUI loss is **available**; see correction below.
- All 21 S1 details lack `manifest_url`; 20 expose `realtime_replay.download_url` ZIPs. These were downloaded and decoded (replay/chunks, events, result); missing modern manifests were **not** treated as missing replays. Arena: 20 segmented manifests, 1,403 segments downloaded and processed. Two upstream malformed JSON lines in two first segments were skipped (checksums matched advertised values); initial errors are retained in `download_errors.json`, recovery/skips in `malformed_frames.log`.
- Retain first frame per 0.5-second bin (~2 Hz); x/y are physics base positions, not intent commands. New frames use command-intent game state and side orientation when available; old frames use latest event state. Old builds have no side intent: assumed home defends left, consistent with goal-crossing directions in every scored/conceded window. Replays remain firstHalf; no side-switch evidence observed. Recorded positions include penalized/off-field robots while state is playing; spatial fractions therefore describe the whole roster, not just active eligible players.
- Event simTime and replay time are aligned by final-event simTime minus manifest duration. This is approximate: offsets range about −0.9 to +1.4 s. Goal windows and event-state boundaries can be shifted by roughly a second plus 0.5-second sampling; interpret as approximate short buildups, not contact-level timing. Goal endpoints have the expected scoring/conceding x sign in all 203 windows, but not all reach the line before the sampled window ends. Position means/roles are more robust than last-contact estimates.
- Travel sums only adjacent playing samples <1 s apart, excluding steps >4 m/s as likely resets/teleports. It undercounts true 10-Hz travel and cannot remove every slow reset. Falling episode counts miss sub-sample falls. No controller source code, successful kick rates, true possession labels, or causal intervention was available.
- S1 is July; recent arena November. Compare within competition/outcome first; do not claim the current arena controller is identical to the championship controller. Opponent baseline is exactly the same available matches, not an independent league sample.
- Files: `fetch.py`, `download.py`, `legacy.py`, `analyze.py`, `report.py`; match details/manifests, legacy ZIPs and 2-Hz samples are fetched into gitignored `data/raw/<UUID>/` directories. CSVs: records, record_summary, opponents, robots, robot_summary, role_summary, teams, team_summary, goals, goal_trajectories, fouls_by_reason, coverage. From this directory: `python fetch.py --snapshot`, `python analyze.py`, `python report.py`. See README.md for dependencies and fresh public-list fetching. The narrative is curated for the committed snapshot, not arbitrary newer data.

### Heatmaps
Normalized attack is rightward; each panel's density is normalized independently (compare spatial shape, not absolute color between panels). Rectangles mark the operational box proxy, not verified official geometry.

![S1 roles](robots_OFFICIAL.png)
![Recent arena roles](robots_FREE_BATTLE.png)
![Ball territory](ball_heatmaps.png)
'''
    text=text.replace('The SUI loss is **available**; see correction below.','The SUI loss is available.')
    (OUT/'champion_analysis.md').write_text(text)
    print('WROTE',OUT/'champion_analysis.md')

if __name__=='__main__':main()
