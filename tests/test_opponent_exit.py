import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS

from team.src import opponent_exit
from team.src.field_logic import run
from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context,
    GameControlState, GameState, Pose2D, SetPlay,
)
import test_team_dispatch as dispatch_tests
from test_throw_in import Receiver


class OpponentExitTest(unittest.TestCase):
    def setUp(self):
        self.context = Context(0, .03, 1, FIELD, game=GameControlState(
            state=GameState.PLAYING, set_play=SetPlay.GOAL_KICK, kicking_team=2),
            ball=BallState(6, 2))

    def test_recorded_endline_exits_move_away_from_post_without_yaw(self):
        for pose in ((7.1618285855,1.7254352588,2.9258986605),
                     (7.1010279964,1.5072479574,2.7708129467)):
            for mirror in (1,-1):
                p=Receiver(2,(pose[0]*mirror,pose[1]*mirror,pose[2]))
                context=replace(self.context,ball=BallState(6*mirror,2*mirror))
                goal=opponent_exit.target(context,p.pose,context.ball)
                self.assertLessEqual(abs(goal[0]),6.7)
                self.assertLessEqual(abs(goal[1]),4.2)
                self.assertGreater(goal[1]*mirror,p.pose.y*mirror)
                legal_after=None
                for step in range(150):
                    opponent_exit.clear(context,[p])
                    if p.calls[-1][0]=='stop':break
                    vx,vy,yaw=p.calls[-1][1]
                    self.assertEqual(yaw,0)
                    self.assertAlmostEqual(math.hypot(vx,vy),.75)
                    c,s=math.cos(p.pose.theta),math.sin(p.pose.theta)
                    wx,wy=c*vx-s*vy,s*vx+c*vy
                    self.assertGreater(wy*mirror,0)
                    p.pose=Pose2D(p.pose.x+wx*.03,p.pose.y+wy*.03,p.pose.theta)
                    if math.hypot(p.pose.x-context.ball.x,p.pose.y-context.ball.y)>1.45 and legal_after is None:
                        legal_after=(step+1)*.03
                self.assertIsNotNone(legal_after)
                self.assertLess(legal_after,3)

    def test_recorded_goal_kick_wait_does_not_stop_with_five_cm_margin(self):
        p=Receiver(3,(4.4291053726,1.8925605968,.3636921062))
        opponent_exit.clear(self.context,[p])
        self.assertEqual(p.calls[-1][0],'velocity')
        moved_ball=replace(self.context,ball=BallState(5.8183894316,1.9801350631))
        opponent_exit.clear(moved_ball,[p])
        self.assertEqual(p.calls[-1][0],'velocity')
        self.assertLess(p.calls[-1][1][0],0)

    def test_throw_in_recovery_filter_remains_in_force(self):
        dispatch_tests.DispatchTest.setUpClass()
        agent=dispatch_tests.DispatchTest.Agent();store=NS();agent.init_store(store)
        p=Receiver(3,(.2858526861,4.4286126436,-.097273708))
        p.ready=False
        context=replace(self.context,ball=BallState(-.4836078015,4.4183193271),game=replace(
            self.context.game,set_play=SetPlay.THROW_IN))
        p.context=context
        agent.play(context,[p],store)
        self.assertEqual(p.action,'recovering')
        self.assertEqual(p.calls,[('stop',)])

    def test_clear_players_stop_and_radial_exit_points_outward(self):
        p=Receiver(2,(3.9,2,0))
        opponent_exit.clear(self.context,[p])
        self.assertEqual(p.calls[-1],('stop',))
        p.pose=Pose2D(5,2,0)
        opponent_exit.clear(self.context,[p])
        self.assertEqual(p.calls[-1][0],'velocity')
        for actual,expected in zip(p.calls[-1][1],(-.75,0.,0.)):
            self.assertAlmostEqual(actual,expected)

    def test_missing_ball_pose_and_empty_roster(self):
        p=Receiver(2,None)
        opponent_exit.clear(self.context,[p])
        self.assertEqual(p.calls[-1],('stop',))
        p.pose=Pose2D(6,2,0)
        opponent_exit.clear(replace(self.context,ball=None),[p])
        self.assertEqual(p.calls[-1],('stop',))
        opponent_exit.clear(self.context,[])

    def test_kickoffs_never_use_exit_controller(self):
        p=Receiver(2,(5,2,0));p.context=self.context
        store=NS(cur_phase=None,prev_phase=None,normal_attacker=None,kickoff_taker=None)
        context=replace(self.context,game=replace(self.context.game,set_play=SetPlay.NONE,secondary_time=10))
        run(context,[p],store)
        self.assertEqual(p.calls[-1][0],'walk')


if __name__=='__main__':
    unittest.main()
