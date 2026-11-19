import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ScoringAnalysisTest(unittest.TestCase):
    def run_fixture(self, commands, game=None, broken=False, deflected=False, ball=None, opponents=None):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);match=root/'batch-01/match-01';match.mkdir(parents=True)
            (match/'summary.json').write_text(json.dumps(dict(side='home')))
            events=[dict(type='ball_touch',actor=dict(side='home'),wallTime=1),dict(type='ball_touch',actor=dict(side='away'),wallTime=3)]
            if deflected:events.append(dict(type='goal',actor=dict(side='home'),wallTime=3.1))
            (match/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            ball=ball or [4,0]
            tick=dict(type='tick',wall=2,dropped=0,writer_error=None,ball=ball,opponents=opponents or {'1':[6,0,0]},
                      game=game or dict(state='PLAYING',stopped=False,set_play='NONE',kicking_team=255,secondary=0),
                      players=[dict(id=2,action='attack',pose=[ball[0]-.5,ball[1],0],commands=commands)])
            with gzip.open(match/'telemetry.jsonl.gz','wt') as f:f.write('{broken' if broken else json.dumps(tick)+'\n')
            command=[sys.executable,str(Path(__file__).parents[1]/'scripts/analyze_scoring.py'),str(root),'--output',str(root/'out.json')]
            p=subprocess.run(command,capture_output=True,text=True)
            return p,json.loads((root/'out.json').read_text()) if p.returncode==0 else None

    def test_blocked_normal_chance_with_clear_alternative(self):
        process,report=self.run_fixture([dict(kind='kick_body')])
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(report['totals']['all_close_requests_center_blocked'],1)
        self.assertEqual(report['totals']['all_center_blocked_with_clear_alternative'],1)

    def test_no_request_and_restart_excluded(self):
        _,report=self.run_fixture([])
        self.assertEqual(report['totals']['no_close_in_range_request'],1)
        _,report=self.run_fixture([],dict(state='PLAYING',stopped=False,set_play='THROW_IN',kicking_team=1,secondary=10))
        self.assertEqual(report['totals'].get('in_range_possessions',0),0)

    def test_malformed_telemetry_is_not_reported_as_zero_chances(self):
        process,report=self.run_fixture([],broken=True)
        self.assertNotEqual(process.returncode,0)
        self.assertIsNone(report)
        self.assertIn('JSONDecodeError',process.stderr)

    def test_goal_after_deflection_is_not_counted_as_a_lost_chance(self):
        _,report=self.run_fixture([dict(kind='kick_body')],deflected=True)
        self.assertEqual(report['totals']['scored'],1)
        self.assertEqual(report['totals']['goals_credited_after_opponent_deflection'],1)
        self.assertEqual(report['totals'].get('all_close_requests_center_blocked',0),0)

    def test_only_real_side_candidates_count_as_alternatives(self):
        _,report=self.run_fixture([dict(kind='kick_body')],ball=[4,2],
                                  opponents={'1':[6,1.24,0],'2':[6,0,0]})
        self.assertEqual(report['totals']['all_close_requests_center_blocked'],1)
        self.assertEqual(report['totals']['all_center_blocked_with_clear_alternative'],0)


if __name__=='__main__':unittest.main()
