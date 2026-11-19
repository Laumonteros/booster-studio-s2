import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReboundAnalysisTest(unittest.TestCase):
    def run_fixture(self, rows, broken=False, failed=False):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);match=root/'batch-01/match-01';match.mkdir(parents=True)
            if failed:(match/'failure.json').write_text('{}')
            with gzip.open(match/'telemetry.jsonl.gz','wt')as f:
                f.write('{broken'if broken else'\n'.join(map(json.dumps,rows)))
            p=subprocess.run([sys.executable,str(Path(__file__).parents[1]/'scripts/analyze_rebounds.py'),str(root),'--output',str(root/'out.json')],capture_output=True,text=True)
            return p,json.loads((root/'out.json').read_text())if p.returncode==0 else None

    def tick(self, time, ball, opponent):
        return dict(type='tick',wall=time,now=time,ball_seen=time,dropped=0,writer_error=None,
                    game=dict(state='PLAYING',stopped=False,set_play='NONE',kicking_team=255,secondary=0),
                    ball=ball,opponents={'1':opponent},players=[
                        dict(id=2,action='attack',pose=[0,0,0],commands=[dict(kind='kick_body')]),
                        dict(id=3,action='support',pose=[-2,1.5,0],commands=[])])

    def test_free_flight_followed_by_opponent_proximity(self):
        p,d=self.run_fixture([self.tick(0,[.3,0],[3,0,0]),self.tick(.1,[1.1,0],[3,0,0]),self.tick(.3,[2.5,0],[3,0,0])])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(d['totals']['loose_windows'],1)
        self.assertEqual(d['totals']['next_proximity_opponent'],1)

    def test_empty_missing_and_restart_data_do_not_invent_recoveries(self):
        _,d=self.run_fixture([]);self.assertEqual(d['totals'],{})
        t=self.tick(0,[.3,0],[3,0,0]);t['ball']=None
        _,d=self.run_fixture([t]);self.assertEqual(d['totals'],{})
        t=self.tick(0,[.3,0],[3,0,0]);t['game']['set_play']='THROW_IN'
        _,d=self.run_fixture([t]);self.assertEqual(d['totals'],{})

    def test_bad_telemetry_is_an_error_not_zero_opportunities(self):
        p,d=self.run_fixture([],broken=True)
        self.assertNotEqual(p.returncode,0);self.assertIsNone(d)
        self.assertIn('JSONDecodeError',p.stderr)

    def test_prestart_failure_is_not_an_analyzed_match(self):
        p,d=self.run_fixture([],failed=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(d['matches'],[])

    def test_goal_zone_opponent_deflection_then_loose_rebound(self):
        rows=[]
        for time,ball,opponent in((0,[.3,0],[3,0,0]),(.1,[1.1,0],[3,0,0]),
                                   (.3,[2.5,0],[3,0,0]),(.8,[1.1,0],[3,0,0]),
                                   (1.,[.5,0],[3,0,0])):
            t=self.tick(time,ball,opponent)
            t['ball']=[ball[0]+3,ball[1]]
            t['opponents']['1'][0]+=3
            for p in t['players']:p['pose'][0]+=3
            rows.append(t)
        p,d=self.run_fixture(rows)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(d['totals']['after_opponent_proximity'],1)


if __name__=='__main__':unittest.main()
