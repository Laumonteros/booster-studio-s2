import math
import unittest
from types import SimpleNamespace

from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context,
    GameControlState, GameState, Pose2D, RobotState, SetPlay,
)
from team.src.player import Player
from team.src.tactics import (
    keeper_can_clear, keeper_target, keeper_tracking_target, phase, retreat_target,
    select_roles, shot_target, support_target,
)


class RolesTest(unittest.TestCase):
    def test_fixed_keeper_never_chases_midfield(self):
        self.assertEqual(select_roles({1: (0, 0), 2: (-2, 0), 3: (-3, 0)}, (0, 0)), (1, 2, 3))

    def test_nearest_roamer(self):
        self.assertEqual(select_roles({1: (-6.6, 0), 2: (-3, 1), 3: (1, 0)}, (0, 0)), (1, 3, 2))

    def test_hysteresis_holds_small_advantage(self):
        self.assertEqual(select_roles({2: (1.4, 0), 3: (1, 0)}, (0, 0), 2)[1], 2)

    def test_hysteresis_switches_large_advantage(self):
        self.assertEqual(select_roles({2: (2, 0), 3: (1, 0)}, (0, 0), 2)[1], 3)

    def test_unavailable_attacker_replaced(self):
        self.assertEqual(select_roles({1: (-6.6, 0), 3: (1, 0)}, (0, 0), 2), (1, 3, None))

    def test_empty_roster(self):
        self.assertEqual(select_roles({}, (0, 0)), (None, None, None))

    def test_unknown_ball(self):
        self.assertEqual(select_roles({1: (-6, 0), 2: (0, 0)}, None), (1, None, None))

    def test_unknown_pose(self):
        self.assertEqual(select_roles({1: None, 2: None, 3: (1, 0)}, (0, 0)), (None, 3, None))

    def test_keeper_only(self):
        self.assertEqual(select_roles({1: (-6, 0)}, (0, 0)), (1, None, None))

    def test_tie_deterministic(self):
        self.assertEqual(select_roles({3: (1, 0), 2: (-1, 0)}, (0, 0))[1], 2)

    def test_invalid_coordinate_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            select_roles({2: (1,)}, (0, 0))


class GeometryTest(unittest.TestCase):
    def test_keeper_deep_and_inside_box(self):
        for ball in ((0, 0), (5, 4), (-6.5, -4), None):
            x, y = keeper_target(FIELD, ball)
            self.assertAlmostEqual(x, -6.6)
            self.assertLess(abs(y), FIELD.goal_area_width / 2)
            self.assertLess(abs(y), FIELD.goal_width / 2)

    def test_keeper_tracks_without_freezing_near_ball(self):
        first, direction = keeper_tracking_target(FIELD, (-6.6, 0), (-5.4, 0), 1)
        self.assertEqual(direction, 1)
        second, direction = keeper_tracking_target(FIELD, first, (-5.4, 0), direction)
        self.assertEqual(direction, -1)
        self.assertGreater(math.dist(first, second), .2)
        self.assertEqual(first[0], second[0])
        self.assertLess(abs(second[1]), FIELD.goal_width / 2)

    def test_keeper_does_not_shuffle_when_ball_unknown_or_far(self):
        for ball in (None, (0, 0)):
            self.assertEqual(keeper_tracking_target(FIELD, (-6.6, 0), ball, 1), (keeper_target(FIELD, ball), 1))

    def test_keeper_clear_requires_box_and_closest(self):
        positions = {1: (-6.6, 0), 2: (-4, 0)}
        self.assertTrue(keeper_can_clear(FIELD, positions, (-6.5, 0), (0, 0)))
        self.assertFalse(keeper_can_clear(FIELD, positions, (-5, 0), (0, 0)))
        self.assertFalse(keeper_can_clear(FIELD, positions, (-6.5, 2.1), (0, 0)))
        self.assertFalse(keeper_can_clear(FIELD, {1: (-6.6, 0), 2: (-6, 0)}, (-6.1, 0), (0, 0)))

    def test_missing_keeper_cannot_clear(self):
        self.assertFalse(keeper_can_clear(FIELD, {}, (-6, 0)))
        self.assertFalse(keeper_can_clear(FIELD, {1: None}, (-6, 0)))
        self.assertFalse(keeper_can_clear(FIELD, {1: (-6, 0)}, None))

    def test_support_spaced_and_in_field(self):
        for ball in ((0, 0), (4, 2), (-6, -4), (6, 4)):
            target = support_target(FIELD, ball)
            self.assertGreater(math.dist(target, ball), 3.0)
            self.assertLess(abs(target[0]), FIELD.length / 2)
            self.assertLess(abs(target[1]), FIELD.width / 2)

    def test_retreat_clearance_even_at_corners(self):
        for ball in ((0, 0), (7, 4.5), (-7, -4.5), (-6.6, 0)):
            position = (ball[0] * .95, ball[1] * .95)
            target = retreat_target(FIELD, position, ball)
            self.assertIsNotNone(target)
            self.assertGreater(math.dist(target, ball), 1.9)
            self.assertLess(abs(target[0]), 7)
            self.assertLess(abs(target[1]), 4.5)

    def test_retreat_safe_or_unknown_stops(self):
        self.assertIsNone(retreat_target(FIELD, (-4, 0), (0, 0)))
        self.assertIsNone(retreat_target(FIELD, (-4, 0), None))

    def test_keeper_retreat_stays_inside_box(self):
        for ball in ((-6.5, 0), (-6, 0), (-6.6, 1), (-6.6, -1), (-6.9, 0)):
            position = (-6.6, 0)
            target = retreat_target(FIELD, position, ball, keeper=True)
            self.assertIsNotNone(target)
            self.assertGreater(math.dist(target, ball), 1.85)
            self.assertGreaterEqual(target[0], -7)
            self.assertLessEqual(target[0], -7 + FIELD.goal_area_length)
            self.assertLessEqual(abs(target[1]), FIELD.goal_area_width / 2)

    def test_restart_no_direct_goal_before_displacement(self):
        for ball in ((0, 0), (-6.8, 0), (6.9, 4.3), (6.5, -4)):
            tx, ty = shot_target(FIELD, ball, ball)
            dx, dy = tx - ball[0], ty - ball[1]
            for goal in (-7, 7):
                t = (goal - ball[0]) / dx
                if t > 0:
                    self.assertGreater(abs(ball[1] + t * dy), FIELD.goal_width / 2)

    def test_shot_after_displacement(self):
        self.assertGreater(shot_target(FIELD, (2, 0), (0, 0))[0], 7)
        self.assertGreater(shot_target(FIELD, (0, 0), None)[0], 7)

    def test_restart_ray_avoids_both_goals_across_field(self):
        for x in (-6.9, -6, -3, 0, 3, 5, 5.9, 6.5, 6.9):
            for y in (-4.4, -2.8, -1.5, 0, 1.5, 2.8, 4.4):
                tx, ty = shot_target(FIELD, (x, y), (x, y))
                self.assertGreaterEqual(tx, x)
                self.assertLess(abs(ty), 4.5)
                for goal in (-7, 7):
                    t = (goal - x) / (tx - x)
                    if t > 0:
                        self.assertGreater(abs(y + t * (ty - y)), FIELD.goal_width / 2 + .5)

    def test_restart_kick_low_power_override(self):
        player = Player(2, None, None)
        player.context = Context(0, .03, 1, FIELD, ball=BallState(0, 0), teammates={2: RobotState(2, Pose2D(-.5, 0, 0))})
        kicks = []
        player.kick = lambda direction, power: kicks.append((direction, power))
        player.attack((1, -.9), power=1.5)
        self.assertAlmostEqual(kicks[0][1], 1.5)


class SafetyTest(unittest.TestCase):
    def context(self, state=GameState.PLAYING, **kwargs):
        return Context(0, 1 / 30, 1, FIELD, game=GameControlState(state=state, **kwargs))

    def test_set_initial_finished_stop(self):
        for state in (GameState.SET, GameState.INITIAL, GameState.FINISHED):
            self.assertEqual(phase(self.context(state)), 'stopped')

    def test_stopped_overrides_ready(self):
        self.assertEqual(phase(self.context(GameState.READY, stopped=True)), 'stopped')

    def test_unknown_game_stops(self):
        self.assertEqual(phase(Context(0, .03, 1, FIELD)), 'stopped')

    def test_restart_ownership_and_release_from_referee(self):
        self.assertEqual(phase(self.context(set_play=SetPlay.THROW_IN, kicking_team=2)), 'their_restart')
        self.assertEqual(phase(self.context(secondary_time=10, kicking_team=1)), 'our_restart')
        self.assertEqual(phase(self.context()), 'normal')

    def test_stop_zeroes_immediately(self):
        backend = SimpleNamespace(set_velocity=lambda *args: calls.append(args), release_kick=lambda: None)
        calls = []
        player = Player(2, None, backend)
        player._last_velocity = (1.5, 0, 1.1)
        player.stop()
        self.assertEqual(calls[-1], (0, 0, 0))

    def test_velocity_slew_limited(self):
        calls = []
        backend = SimpleNamespace(set_velocity=lambda *args: calls.append(args))
        player = Player(2, None, backend)
        player.context = self.context()
        player.set_velocity(2, 1, 3)
        self.assertLessEqual(abs(calls[-1][0]), .061)
        self.assertLessEqual(abs(calls[-1][2]), .067)


if __name__ == '__main__':
    unittest.main()
