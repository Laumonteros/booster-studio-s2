import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('telemetry_analysis', Path(__file__).parents[1] / 'scripts/analyze_telemetry.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AnalysisTest(unittest.TestCase):
    def test_warning_owner_retake_is_opposite_awarded_side(self):
        self.assertEqual(analysis.owner({'type':'set_play_retake','actor':{'side':'away'},'outcome':{}}),'home')

    def test_lane_empty_blocked_and_degenerate(self):
        self.assertEqual(analysis.lane_distance((0,0),(0,0),{}),0)
        self.assertEqual(analysis.lane_distance((0,0),(7,0),{}),100)
        self.assertEqual(analysis.lane_distance((0,0),(7,0),{'1':[3,0,0]}),0)

    def fixture(self, directory):
        p = dict(id=2,role='attacker',action='roamer:attack',pose=[2.2,0,0],native_active=True,kicking=True,
                 calls=[dict(method='attack',args=[[7.25,0]],kwargs={})],
                 commands=[dict(kind='kick_body',direction=0,power=5.5)])
        ticks = [dict(type='tick',wall=t,wall_end=t+.001,now=t,team=1,dropped=0,writer_error=None,
                      ball=[2.8,0],opponents={},game=dict(state='PLAYING',stopped=False),players=[p]) for t in (2.1,2.2,2.9)]
        native = [dict(type=kind,robot=2,wall=t,reason='roamer:attack/attack/release_kick',thread='test')
                  for kind,t in (('native_start_request',2),('native_start',2.05),('native_stop_request',3),('native_stop',3.01))]
        with gzip.open(directory/'telemetry.jsonl.gz','wt') as f:
            f.write('\n'.join(json.dumps(r) for r in ticks+native)+'\n')
        events = [dict(type='ball_touch',actor=dict(side='home'),wallTime=2,severity='info'),
                  dict(type='goal',actor=dict(side='away'),wallTime=3,severity='info'),
                  dict(type='match_finished',actor=None,wallTime=4,severity='info')]
        (directory/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')

    def test_sessions_reach_possessions_and_pre_goal_context(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.fixture(path)
            report = analysis.analyze(path)
        a = report['aggregate']
        self.assertEqual(a['roamer_sessions'],1)
        self.assertEqual(a['roamer_reach_episodes'],{2:1})
        self.assertEqual(a['sessions_per_possession'],[1])
        self.assertEqual(a['conceded_goals'],1)
        self.assertEqual(a['blocked_kick_ticks'],0)
        self.assertAlmostEqual(report['event_contexts'][0]['observation_age'],.1)

    def test_missing_backend_coverage_is_rejected_not_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.fixture(path)
            with gzip.open(path/'telemetry.jsonl.gz','rt') as f:rows=[json.loads(s) for s in f]
            with gzip.open(path/'telemetry.jsonl.gz','wt') as f:f.write('\n'.join(json.dumps(r) for r in rows if r['type']=='tick'))
            with self.assertRaisesRegex(AssertionError,'backend not instrumented'):
                analysis.analyze(path)


if __name__=='__main__':
    unittest.main()
