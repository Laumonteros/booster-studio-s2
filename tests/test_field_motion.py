import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock

from team.src.field_motion import limit_velocity
from team.src.field_player import Player
from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context,
    GameControlState, GameState, Pose2D, SetPlay,
)


class FieldMotionTest(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.player = Player(2, NS(team_id=1), self.backend)
        self.player.action = 'attack'
        self.context = Context(0, .03, 1, FIELD, game=GameControlState(state=GameState.PLAYING),
                               ball=BallState(2, 0), teammates={2:NS(pose=Pose2D())},
                               opponents={2:NS(pose=Pose2D(.3, 0, 0))})
        self.player.context = self.context

    def test_real_player_limits_close_opponent_and_preserves_yaw(self):
        self.player.set_velocity(2., 0., .3)
        self.backend.set_velocity.assert_called_once_with(.75, 0., .3)

    def test_teammate_and_lateral_close_approaches_preserve_direction(self):
        self.player.context = replace(self.context, opponents={}, teammates={
            2:NS(pose=Pose2D()), 1:NS(pose=Pose2D(0, .3, 0))})
        x,y,yaw=limit_velocity(self.player, 1.2, 1.6, .8)
        self.assertAlmostEqual(math.hypot(x,y),.75)
        self.assertAlmostEqual(x/y,1.2/1.6)
        self.assertEqual(yaw,.8)

    def test_soft_band_and_free_running_keep_normal_attack_fast(self):
        for distance in (.5,.6,.7,.8,.85,2.):
            self.player.context=replace(self.context,opponents={1:NS(pose=Pose2D(distance,0,0))})
            x,y,w=limit_velocity(self.player,2.,0.,.2)
            expected=.75+1.25*max(0,min(1,(distance-.5)/.35))
            self.assertAlmostEqual(x,expected)
        self.assertEqual((x,y,w),(2.,0.,.2))

    def test_already_slow_stop_and_turn_only_are_exact_passthrough(self):
        for velocity in ((.2,.3,.8),(0.,0.,2.),(0.,0.,0.),(.75,0.,-.2)):
            self.assertEqual(limit_velocity(self.player,*velocity),velocity)

    def test_only_normal_attacking_action_is_limited(self):
        for action in ('support','restart:receive_position','restart:second_touch',
                       'restart:short_pass','opp_set:retreat','kickoff','ready','stopped'):
            self.player.action=action
            self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))

    def test_all_set_plays_and_ownership_exclusions(self):
        for play in SetPlay:
            if play==SetPlay.NONE:continue
            for team in (1,2):
                self.player.context=replace(self.context,game=replace(self.context.game,set_play=play,kicking_team=team))
                self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))
        for team in (1,2):
            self.player.context=replace(self.context,game=replace(self.context.game,kicking_team=team,secondary_time=10))
            self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))

    def test_keeper_other_states_and_unknown_inputs_are_passthrough(self):
        for state in GameState:
            if state==GameState.PLAYING:continue
            self.player.context=replace(self.context,game=replace(self.context.game,state=state))
            self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))
        for context in (None,replace(self.context,game=None),replace(self.context,teammates={}),
                        replace(self.context,game=replace(self.context.game,stopped=True))):
            self.player.context=context
            self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))
        self.player.context=self.context
        self.player.id=1
        self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))

    def test_own_pose_is_not_an_obstacle_and_unknown_robots_are_skipped(self):
        self.player.context=replace(self.context,opponents={1:NS(pose=None)},teammates={2:NS(pose=Pose2D()),3:NS(pose=None)})
        self.assertEqual(limit_velocity(self.player,2.,0.,1.),(2.,0.,1.))

    def test_native_kick_requests_are_not_modified(self):
        self.player.kick(.4,5.)
        self.backend.kick.assert_called_once_with(.4,5.,2.,0.)
        self.backend.set_velocity.assert_not_called()

    def test_recorded_crowded_full_speed_windows_are_limited(self):
        for separation in (.2699739367,.2594527449):
            self.player.context=replace(self.context,opponents={1:NS(pose=Pose2D(separation,0,0))})
            x,y,_=limit_velocity(self.player,2.,0.,.3)
            self.assertLess(math.hypot(x,y),2.)


if __name__=='__main__':
    unittest.main()
