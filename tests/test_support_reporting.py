import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('support_report',Path(__file__).parents[1]/'scripts/check_support_telemetry.py')
report=importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class SupportReportTest(unittest.TestCase):
    def test_empty_and_observed_range_summary(self):
        self.assertEqual(report.summary([]),{'samples':0})
        self.assertEqual(report.summary([1,2,3])['median'],2)
        self.assertAlmostEqual(report.summary([1,2,3])['fraction_1_5_to_2_5'],1/3)

    def test_actual_distance_is_not_confused_with_target(self):
        tick=dict(type='tick',dropped=0,writer_error=None,ball=[-2,0],game=dict(state='PLAYING',stopped=False,set_play='NONE',kicking_team=255),
            players=[dict(id=2,role='attacker',action='attack',pose=[-2,0,0]),
                     dict(id=3,role='support',action='support',pose=[-5,0,0],calls=[dict(method='move_to_position',args=[[-4,0]])])])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trace.gz'
            with gzip.open(path,'wt') as f:f.write(json.dumps(tick)+'\n'+json.dumps(dict(type='native_start'))+'\n')
            result,*_=report.distances(path)
        self.assertEqual(result['support_ball']['median'],3)
        self.assertEqual(result['target_ball']['median'],2)
        self.assertEqual(result['support_carrier_within_1m_of_ball']['median'],3)

    def test_empty_trace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trace.gz'
            with gzip.open(path,'wt'):pass
            with self.assertRaises(AssertionError):report.distances(path)


if __name__=='__main__':unittest.main()
