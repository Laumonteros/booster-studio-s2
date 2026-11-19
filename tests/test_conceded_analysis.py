import unittest

from scripts.analyze_conceded import contact_limit,crossing,nearest


class ConcededAnalysisTest(unittest.TestCase):
    def test_crossing_interpolates_moving_keeper_and_ball(self):
        samples=[dict(wall=1,ball=(-6.5,.8),players={'1':dict(pose=(-6.6,.1,0))}),
                 dict(wall=1.1,ball=(-6.7,.6),players={'1':dict(pose=(-6.6,.2,0))})]
        result=crossing(samples)
        self.assertAlmostEqual(result['wall'],1.05)
        self.assertAlmostEqual(result['ball_y'],.7)
        self.assertAlmostEqual(result['lateral_gap'],.55)

    def test_empty_stale_missing_pose_or_ball_do_not_invent_crossing(self):
        self.assertIsNone(crossing([]));self.assertIsNone(nearest([],[],1))
        for pose,ball in((None,(-7,0)),((-6.6,0,0),None)):
            self.assertIsNone(crossing([dict(wall=1,ball=ball,players={'1':dict(pose=pose)}),
                                        dict(wall=2,ball=(-7.2,0),players={'1':dict(pose=(-6.6,0,0))})]))

    def test_nearest_does_not_use_future_observation(self):
        self.assertEqual(nearest(['a','b'],[1,2],1.9),'a')
        self.assertIsNone(nearest(['a','b'],[1,2],.5))

    def test_binding_requires_proximity_request_and_accepted_saturated_command(self):
        keeper=dict(pose=(-6.6,0,0),walk=(-6.6,.8),action='keeper:intercept',commands=[dict(kind='velocity_body',accepted=True,velocity=(0,.75,0))])
        self.assertTrue(contact_limit({'1':keeper},{'2':(-6.2,0,0)})['binding'])
        self.assertFalse(contact_limit({'1':keeper},{'2':(-4,0,0)})['binding'])
        keeper['commands'][0]['accepted']=False
        self.assertFalse(contact_limit({'1':keeper},{'2':(-6.2,0,0)})['binding'])
        self.assertIsNone(contact_limit({},{}))


if __name__=='__main__':unittest.main()
