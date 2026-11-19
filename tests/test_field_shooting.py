import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock

from team.src.field_player import Player
from team.src.field_shooting import clearance, shot_target
from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context, GameControlState,
    GameState, Pose2D, SetPlay,
)


class ShootingTest(unittest.TestCase):
    def setUp(self):
        self.player=Player(2,NS(team_id=1),Mock())
        self.player.action='attack'
        self.context=Context(0,.03,1,FIELD,game=GameControlState(state=GameState.PLAYING),
                             ball=BallState(4.,0.),teammates={2:NS(pose=Pose2D(3.5,0.,0.))},
                             opponents={1:NS(pose=Pose2D(6.,0.,0.))})
        self.player.context=self.context

    def test_blocked_center_chooses_clear_inside_post_target(self):
        target=shot_target(self.player)
        self.assertEqual(target[0],7.)
        self.assertAlmostEqual(abs(target[1]),1.)
        self.assertGreaterEqual(clearance(self.context.ball,target,self.context.opponents),.45)

    def test_real_plan_and_native_kick_use_selected_lane_without_releasing(self):
        direction,power=self.player.plan_kick()
        self.assertAlmostEqual(abs(direction),math.atan2(1.,3.))
        self.assertEqual(power,5.)
        self.player.attack()
        self.player._backend.kick.assert_called_once()
        self.player._backend.release_kick.assert_not_called()

    def test_clear_center_no_opponents_unknown_and_behind_goal(self):
        for opponents in ({},{1:NS(pose=None)},{1:NS(pose=Pose2D(2.,0.,0.))}):
            self.player.context=replace(self.context,opponents=opponents)
            self.assertEqual(shot_target(self.player),(7.25,0.))

    def test_clear_center_preserves_original_behind_goal_aim(self):
        self.player.context=replace(self.context,ball=BallState(4.,1.),opponents={})
        self.assertEqual(shot_target(self.player),(7.25,0.))
        self.assertAlmostEqual(self.player.plan_kick()[0],math.atan2(-1.,3.25))

    def test_hysteresis_keeps_clear_lane_when_other_side_becomes_better(self):
        target=shot_target(self.player)
        self.player.context=replace(self.context,opponents={1:NS(pose=Pose2D(6.,.02,0.))})
        self.assertEqual(shot_target(self.player),target)
        self.player.context=replace(self.context,opponents={1:NS(pose=Pose2D(6.,target[1]*.7,0.)),2:NS(pose=Pose2D(6.,0.,0.))})
        self.assertEqual(shot_target(self.player),(7.,-target[1]))

    def test_all_protected_actions_and_restarts_bypass(self):
        for action in ('support','restart:receive_position','restart:second_touch','restart:short_pass','opp_set:retreat','kickoff','ready','stopped'):
            self.player.action=action
            self.assertIsNone(shot_target(self.player))
        self.player.action='attack'
        for play in SetPlay:
            if play==SetPlay.NONE:continue
            for team in (1,2):
                self.player.context=replace(self.context,game=replace(self.context.game,set_play=play,kicking_team=team))
                self.assertIsNone(shot_target(self.player))
                self.assertEqual(self.player.plan_kick(),(0.,5.))

    def test_pauses_missing_state_pose_ball_keeper_and_far_ball(self):
        for context in (None,replace(self.context,game=None),replace(self.context,ball=None),
                        replace(self.context,teammates={}),replace(self.context,game=replace(self.context.game,stopped=True)),
                        replace(self.context,game=replace(self.context.game,state=GameState.SET)),
                        replace(self.context,game=replace(self.context.game,kicking_team=1,secondary_time=10)),
                        replace(self.context,ball=BallState(0.,0.)),replace(self.context,ball=BallState(7.1,0.))):
            self.player.context=context
            self.assertIsNone(shot_target(self.player))
        self.player.context=self.context
        self.player.id=1
        self.assertIsNone(shot_target(self.player))

    def test_missing_observations_plan_still_stops_without_kick(self):
        self.player.context=replace(self.context,ball=None)
        self.assertIsNone(self.player.plan_kick())
        self.player.attack()
        self.player._backend.kick.assert_not_called()


if __name__=='__main__':unittest.main()
