import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS

from team.src import throw_in
from team.src.field_logic import run
from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context, GameControlState,
    GameState, Pose2D, SetPlay,
)
from test_team_dispatch import FakePlayer


class Receiver(FakePlayer):
    def release_kick(self):
        self.calls.append(('release',))

    def set_velocity(self, *velocity):
        self.calls.append(('velocity', velocity))


class ThrowInTest(unittest.TestCase):
    def setUp(self):
        self.store = NS(cur_phase=None, prev_phase=None, normal_attacker=None, kickoff_taker=None)
        self.context = Context(0, .03, 1, FIELD, ball=BallState(0, 4.45), game=GameControlState(
            state=GameState.PLAYING, kicking_team=1, set_play=SetPlay.THROW_IN))
        self.players = [Receiver(2, (-.5, 4, 0)), Receiver(3, (0, 2.65, 0))]
        self.bind()

    def bind(self):
        for p in self.players:
            p.context = self.context

    def step(self):
        self.bind()
        return throw_in.handle(self.context, self.players, self.store)

    def test_only_our_throw_in_starts_handoff(self):
        for set_play in SetPlay:
            for team in (1, 2):
                self.store.throw_in = None
                self.context = replace(self.context, game=replace(self.context.game, set_play=set_play, kicking_team=team))
                self.assertEqual(self.step(), set_play == SetPlay.THROW_IN and team == 1)

    def test_kickoff_keeps_sample_kick_and_no_handoff(self):
        self.context = replace(self.context, ball=BallState(), game=replace(
            self.context.game, set_play=SetPlay.NONE, secondary_time=10))
        self.players[0].pose = Pose2D(-1, 0, 0)
        self.bind()
        run(self.context, self.players, self.store)
        self.assertEqual(self.players[0].calls[-1], ('kick', .1, 5.0))
        self.assertIsNone(self.store.throw_in)

    def test_first_pass_is_low_power_and_receiver_is_different(self):
        self.step()
        self.assertEqual(self.players[0].calls[-1], ('kick', -math.pi / 2, 1.5))
        self.assertEqual(self.store.throw_in['receiver'], 3)
        self.assertEqual(self.players[1].calls[-1][0], 'velocity')

    def test_receiver_keeps_moving_after_ball_free_and_timeout(self):
        self.step()
        self.context = replace(self.context, now=100, game=GameControlState(state=GameState.PLAYING))
        self.step()
        self.assertEqual(self.players[1].calls[-1][0], 'velocity')
        self.assertGreater(math.hypot(*self.players[1].calls[-1][1][:2]), 0)
        self.assertEqual(self.players[0].calls[-1][-1], 1.5)

    def test_receiver_shuttles_for_thirty_seconds_without_idle(self):
        self.step()
        positions = []
        for i in range(1000):
            self.context = replace(self.context, now=i * .03,
                                   game=GameControlState(state=GameState.PLAYING))
            self.step()
            p = self.players[1]
            vx, vy, yaw = p.calls[-1][1]
            self.assertLessEqual(math.hypot(vx, vy), .25 + 1e-8)
            self.assertEqual(yaw, 0)
            p.pose = Pose2D(p.pose.x + vx * .03, p.pose.y + vy * .03, 0)
            positions.append(p.pose.x)
        for i in range(0, 700, 100):
            self.assertGreater(max(positions[i:i+300]) - min(positions[i:i+300]), .8)

    def test_patrol_endpoints_and_field_boundaries(self):
        for x in (-6.9, 6.9):
            t = throw_in.pass_target(self.context, (x, 4.45))
            self.assertLessEqual(abs(t[0]) + .55, 6.65 + 1e-8)
        self.step()
        pending = self.store.throw_in
        self.players[1].pose = Pose2D(pending['target'][0] + .55, pending['target'][1], 0)
        self.step()
        self.assertEqual(pending['side'], -1)

    def test_near_ball_approach_never_waits_for_planner_at_center(self):
        self.players[1].pose = Pose2D(1, 4, 0)
        self.step()
        self.assertEqual(self.players[1].calls[-1][0], 'velocity')
        self.assertGreater(math.hypot(*self.players[1].calls[-1][1][:2]), 0)

    def test_handoff_restricts_shot_then_uses_other_robot(self):
        self.step()
        self.context = replace(self.context, ball=BallState(0, 3.65), game=GameControlState(state=GameState.PLAYING))
        self.step()
        self.assertEqual(self.players[1].calls[-1][-1], 1.5)
        self.context = replace(self.context, ball=BallState(0, 3.2))
        self.step()
        self.assertEqual(self.players[1].calls[-1][0], 'attack')
        self.assertNotEqual(self.players[0].calls[-1][0], 'attack')

    def test_other_restarts_cancel_old_latch(self):
        for set_play in (SetPlay.NONE, SetPlay.GOAL_KICK, SetPlay.INDIRECT_FREE_KICK):
            self.context = replace(self.context, game=replace(self.context.game, set_play=SetPlay.THROW_IN))
            self.step()
            self.context = replace(self.context, game=replace(self.context.game, set_play=set_play))
            self.assertFalse(self.step())
            self.assertIsNone(self.store.throw_in)

    def test_pauses_missing_game_ball_and_empty_roster(self):
        self.step()
        self.context = replace(self.context, ball=None)
        self.assertTrue(self.step())
        self.assertTrue(all(p.calls[-1] == ('stop',) for p in self.players))
        self.context = replace(self.context, game=replace(self.context.game, stopped=True))
        self.assertFalse(self.step())
        self.context = replace(self.context, game=None)
        self.assertFalse(self.step())
        self.players = []
        self.assertFalse(self.step())


if __name__ == '__main__':
    unittest.main()
