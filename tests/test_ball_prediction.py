import math
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from team.src.ball_prediction import BallPredictor
from team.src.field_params import BALL_PRED_FRICTION, BALL_PRED_HORIZON_S, CHASE_BEHIND_M
from team.src.field_player import Player, _behind_ball
from team.src.field_logic import run
from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context, Pose2D,
    GameControlState, GameState,
)


class BallPredictionTest(unittest.TestCase):
    def moving(self, vx=2., vy=0., origin=(0., 0.)):
        predictor = BallPredictor()
        for i in range(9):
            t = i * .03
            ball = BallState(origin[0] + vx*t, origin[1] + vy*t, t)
            predictor.observe(ball, t)
        return predictor, ball

    def test_smoothed_fit_and_friction_capped_horizon(self):
        predictor, ball = self.moving()
        self.assertAlmostEqual(predictor.velocity[0], 2.)
        target = predictor.target(ball, Pose2D(-4., 0.), FIELD)
        expected = 2 * -math.expm1(-BALL_PRED_FRICTION * BALL_PRED_HORIZON_S) / BALL_PRED_FRICTION
        self.assertAlmostEqual(target[0] - ball.x, expected)
        self.assertLess(expected, 2 * BALL_PRED_HORIZON_S)
        self.assertLess(len(predictor.samples), 12)

    def test_stationary_slow_single_and_empty(self):
        for speed in (0., .1):
            predictor, ball = self.moving(speed)
            self.assertEqual(predictor.target(ball, Pose2D(-4, 0), FIELD), (ball.x, ball.y))
        predictor = BallPredictor()
        ball = BallState(1., 2., 1.)
        self.assertEqual(predictor.target(ball, None, FIELD), (1., 2.))
        predictor.observe(ball, 1.)
        self.assertEqual(predictor.velocity, (0., 0.))

    def test_missing_stale_invalid_phase_and_teleport_reset(self):
        for ball, now, enabled in (
            (None, .25, True), (BallState(1., 0., .24), 1., True),
            (BallState(float('nan'), 0., .25), .25, True),
            (BallState(1., 0., .25), .25, False),
            (BallState(0., 0., .1), .25, True),
            (BallState(7., 0., .25), .25, True),
            (BallState(1., 0., 2.), 2., True),
            (BallState(1., 0., 2.), .25, True),
        ):
            with self.subTest(ball=ball, enabled=enabled):
                predictor, _ = self.moving()
                predictor.observe(ball, now, enabled)
                self.assertEqual(predictor.velocity, (0., 0.))

    def test_duplicate_observation_does_not_add_samples(self):
        predictor, ball = self.moving()
        count = len(predictor.samples)
        predictor.observe(ball, .3)
        self.assertEqual(len(predictor.samples), count)
        self.assertAlmostEqual(predictor.velocity[0], 2.)

    def test_field_dispatch_clears_motion_on_goal_ready_and_kickoff(self):
        for game in (GameControlState(state=GameState.READY),
                     GameControlState(state=GameState.SET),
                     GameControlState(state=GameState.PLAYING, secondary_time=5, kicking_team=1)):
            predictor, ball = self.moving()
            store = NS(cur_phase=None, prev_phase=None, normal_attacker=None,
                       kickoff_taker=None, ball_predictor=predictor)
            context = Context(.24, .03, 1, FIELD, ball=ball, game=game)
            run(context, [], store)
            self.assertEqual(predictor.velocity, (0., 0.))

    def test_both_field_edges_clamped(self):
        for sign in (-1, 1):
            predictor, ball = self.moving(sign*2., sign*2., (sign*6., sign*3.5))
            x, y = predictor.target(ball, Pose2D(), FIELD)
            self.assertLessEqual(abs(x), 6.7)
            self.assertLessEqual(abs(y), 4.2)

    def test_roamer_chase_and_support_use_prediction_but_kick_uses_observation(self):
        predictor, ball = self.moving()
        player = Player(2, NS(team_id=1), Mock())
        player._ball_predictor = predictor
        player.context = Context(.24, .03, 1, FIELD, ball=ball,
                                 teammates={2: NS(pose=Pose2D(-4, 0))})
        with patch.object(player, 'walk_to') as walk:
            player.attack((7.25, 0.))
        self.assertGreater(walk.call_args.args[0][0], ball.x)
        with patch.object(player, 'move_to_position') as move:
            player.support()
        self.assertGreater(move.call_args.args[0][0], ball.x - 2.)
        player.context.teammates[2] = NS(pose=Pose2D(ball.x - .5, 0))
        with patch.object(player, 'kick') as kick:
            player.attack()
        kick.assert_called_once()
        self.assertEqual(player.context.ball, ball)

    def test_slow_ball_chase_identical(self):
        predictor, ball = self.moving(.1)
        player = Player(2, NS(team_id=1), Mock())
        player._ball_predictor = predictor
        player.context = Context(.24, .03, 1, FIELD, ball=ball,
                                 teammates={2: NS(pose=Pose2D(-4, 0))})
        with patch.object(player, 'walk_to') as walk:
            player.attack((7.25, 0.))
        self.assertEqual(walk.call_args.args[0], _behind_ball(ball.x, ball.y, (7.25, 0.), CHASE_BEHIND_M))


if __name__ == '__main__':
    unittest.main()
