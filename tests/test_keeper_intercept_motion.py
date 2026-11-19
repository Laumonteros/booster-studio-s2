import math
import unittest
from dataclasses import replace
from types import SimpleNamespace

from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD, Context, Pose2D, RobotState
from team.src.player import Player
from team.src.param import MAX_ANGULAR,MAX_LINEAR,TURN_SPEED_REDUCTION


class KeeperInterceptMotionTest(unittest.TestCase):
    def player(self, player_id=1, action='keeper:intercept', neighbour=True):
        p=Player(player_id,SimpleNamespace(team_id=1),SimpleNamespace(set_velocity=lambda *v:None,release_kick=lambda:None))
        p.context=Context(0,.03,1,FIELD,teammates={player_id:RobotState(player_id,Pose2D(-6.6,0,0))},
                          opponents={2:RobotState(2,Pose2D(-6,.1,0))}if neighbour else{})
        p.action=action
        return p

    def settle(self,p,velocity):
        for _ in range(50):p.set_velocity(*velocity)
        return p._last_velocity

    def test_incoming_keeper_retains_uncrowded_translation(self):
        self.assertEqual(self.settle(self.player(),(0,-1.2,0)),(0,-1.2,0))

    def test_tracking_clearing_ready_and_restart_still_slow(self):
        for action in('keeper:track','keeper:clear','ready','restart:clearance'):
            with self.subTest(action=action):
                self.assertEqual(self.settle(self.player(action=action),(0,-1.2,0)),(0,-.75,0))

    def test_non_keeper_never_gets_exception_even_if_mislabelled(self):
        self.assertEqual(self.settle(self.player(player_id=2),(0,-1.2,0)),(0,-.75,0))

    def test_preserves_global_cap_yaw_reduction_and_acceleration(self):
        p=self.player();p.set_velocity(0,-5,5)
        self.assertAlmostEqual(p._last_velocity[1],-1.8*.03)
        self.assertAlmostEqual(p._last_velocity[2],2*.03)
        vx,vy,yaw=self.settle(p,(0,-5,5))
        self.assertAlmostEqual(math.hypot(vx,vy),MAX_LINEAR/(1+TURN_SPEED_REDUCTION*MAX_ANGULAR))
        self.assertEqual(yaw,MAX_ANGULAR)

    def test_stop_stays_immediate(self):
        p=self.player();self.settle(p,(0,-1.2,0));p.stop()
        self.assertEqual(p._last_velocity,(0,0,0))

    def test_empty_missing_pose_and_context_remain_safe(self):
        p=self.player(neighbour=False)
        self.assertEqual(self.settle(p,(0,-1.2,0)),(0,-1.2,0))
        p.context=replace(p.context,teammates={1:RobotState(1,None)})
        self.assertEqual(self.settle(p,(0,-1.2,0)),(0,-1.2,0))
        p.context=None
        self.assertEqual(self.settle(p,(0,-1.2,0)),(0,-1.2,0))

    def test_recorded_v11_intercept_releases_binding_cap_without_jump(self):
        p=self.player();pose=(-6.574187362949713,-.07786998917705835,-.02377189205545882)
        p.context=replace(p.context,teammates={1:RobotState(1,Pose2D(*pose)),2:RobotState(2,Pose2D(-5.864310008140106,-.36415204180422517,-.6826904486478895))},opponents={})
        previous=(-.005808783488198892,-.7359801291249554,.04754378411091764)
        p._last_velocity=previous
        p.walk_to((-6.5995145782646665,-.8774689712702012),face=0)
        self.assertLess(p._last_velocity[1],previous[1]-.04)
        for old,new,limit in zip(previous,p._last_velocity,(1.8*.03,1.8*.03,2*.03)):
            self.assertLessEqual(abs(new-old),limit+1e-10)


if __name__=='__main__':unittest.main()
