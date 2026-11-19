import unittest

from scripts.estimate_keeper_options import clearance, rollout, segment_gap, validate_goals


class KeeperEstimateTest(unittest.TestCase):
    def test_segment_projection_and_endpoint_clamps(self):
        self.assertEqual(segment_gap((1, 2), (0, 0), (3, 0)), 2)
        self.assertEqual(segment_gap((-1, 0), (0, 0), (3, 0)), 1)
        self.assertEqual(segment_gap((4, 0), (0, 0), (3, 0)), 1)
        self.assertEqual(segment_gap((1, 0), (0, 0), (0, 0)), 1)

    def test_empty_and_single_sample_have_no_crossing(self):
        self.assertIsNone(rollout(dict(trajectory=[]), .4, .15))
        self.assertIsNone(rollout(dict(trajectory=[{}]), .4, .15))

    def test_crossing_is_interpolated_for_new_and_legacy_models(self):
        samples = [dict(wall=i, ball=ball, phase='normal', velocity=(-2, 0),
                        players={'1':dict(pose=(-6.6, 0, 0),action='keeper:intercept')})
                   for i,ball in enumerate([(-6, 0), (-7, 0)])]
        for legacy in (False, True):
            self.assertEqual(rollout(dict(trajectory=samples), .4, .15, legacy), 0)

    def test_keeper_contact_does_not_imply_clearance(self):
        self.assertIsNone(clearance(dict(confirmed_preceding_keeper_touch=False)))
        report=clearance(dict(confirmed_preceding_keeper_touch=True,turnover=dict(wallTime=2),
                              trajectory=[],event_id='goal',match='match'))
        self.assertEqual(report['kind'],'no_observed_clear_request')

    def test_clearance_geometry_and_observed_forward_progress(self):
        sample=dict(wall=1,ball=(-6,0),opponents={'1':(-5,0,0),'2':None},
                    players={'1':dict(action='keeper:clear',pose=(-6.5,0,0),
                                      commands=[dict(kind='kick_body',direction=0)])})
        goal=dict(confirmed_preceding_keeper_touch=True,turnover=dict(wallTime=2),
                  trajectory=[sample,dict(sample,wall=2,ball=(-5.5,0))],event_id='goal',match='match')
        report=clearance(goal)
        self.assertEqual(report['kind'],'observed_clear_request')
        self.assertEqual(report['centre_first_3m_lane_gap'],0)
        self.assertTrue(report['estimated_outlet_gain'])
        self.assertEqual(report['max_forward_progress'],.5)
        self.assertEqual(report['requested_field_angles'],[0])

    def test_matching_empty_or_duplicate_goal_inputs(self):
        validate_goals([],[])
        row=dict(version='v9',batch='batch-01',match='match-01',sim_time='1.234',keeper_status='miss')
        goal=dict(match='v9/batch-01/match-01',sim_time=1.2341,category='miss')
        validate_goals([row],[goal])
        with self.assertRaisesRegex(ValueError,'same goals'):
            validate_goals([row,row],[goal])
