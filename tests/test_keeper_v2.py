import io
import json
import math
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from team.src import tactics
from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD, Context
from team.src.tactics import (
    keeper_can_clear, keeper_intercept, keeper_target, keeper_tracking_target,
    keeper_velocity_update, keeper_waypoint,
)


class KeeperPositionTest(unittest.TestCase):
    def test_angle_line_is_compressed_toward_centre(self):
        self.assertAlmostEqual(keeper_target(FIELD, (-3, 2))[1], .17)
        self.assertAlmostEqual(keeper_target(FIELD, (-3, -2))[1], -.17)
        self.assertEqual(keeper_target(FIELD, None), (-6.6, 0))

    def test_near_goal_clamps_inside_posts(self):
        self.assertEqual(keeper_target(FIELD, (-7, 4))[1], 1)
        self.assertEqual(keeper_target(FIELD, (-8, -4))[1], -1)

    def test_short_waypoint_preserves_direction(self):
        point = keeper_waypoint((-6.6, -1), (-6.6, 1))
        self.assertAlmostEqual(point[0], -6.6)
        self.assertAlmostEqual(point[1], -.2)
        self.assertEqual(keeper_waypoint((-6.6, 0), (-6.6, 0)), (-6.6, 0))

    def test_ball_behind_nominal_line_uses_safe_backstop(self):
        self.assertAlmostEqual(keeper_target(FIELD, (-6.8, .5))[0], -6.85)

    def test_shuffle_endpoints_do_not_collapse_at_post(self):
        first, direction = keeper_tracking_target(FIELD, (-6.85, -.85), (-6.95, -1.35), -1)
        self.assertGreater(math.dist(first, (-6.85, -.85)), .15)
        second, _ = keeper_tracking_target(FIELD, first, (-6.95, -1.35), direction)
        self.assertAlmostEqual(math.dist(first, second), .7)
        self.assertLessEqual(abs(first[1]), 1)
        self.assertLessEqual(abs(second[1]), 1)


class KeeperVelocityTest(unittest.TestCase):
    def update(self, previous, ball, stamp, now=None, phase='normal'):
        return keeper_velocity_update(previous, ball, stamp, stamp if now is None else now, phase)

    def test_two_samples_then_filter(self):
        first = self.update(None, (-3, 1), 1)
        self.assertIsNone(first[2])
        second = self.update(first, (-3.2, .9), 1.1)
        self.assertAlmostEqual(second[2][0], -2)
        third = self.update(second, (-3.2, .9), 1.2)
        self.assertAlmostEqual(third[2][0], -.7)

    def test_repeated_observation_not_zero_velocity(self):
        previous = ((-3, 1), 1, (-2, 0))
        self.assertEqual(self.update(previous, (-3, 1), 1, 1.1), previous)

    def test_missing_stale_and_restart_reset(self):
        previous = ((-3, 1), 1, (-2, 0))
        self.assertIsNone(self.update(previous, None, 1.1))
        self.assertIsNone(self.update(previous, (-3, 1), 1, 2))
        self.assertIsNone(self.update(previous, (-3, 1), 1.1, phase='our_restart'))
        self.assertIsNone(self.update(previous, (-3, 1), 1.1, phase='stopped'))

    def test_teleport_gap_backwards_and_nonfinite_reset(self):
        previous = ((-3, 1), 1, (-2, 0))
        for ball, stamp in [((0, 0), 1.1), ((-3, 1), 2), ((-3, 1), .9)]:
            self.assertIsNone(self.update(previous, ball, stamp)[2])
        self.assertIsNone(self.update(previous, (math.nan, 1), 1.1))


class KeeperPredictionTest(unittest.TestCase):
    def test_diagonal_projects_far_side_not_current_ball_y(self):
        target = keeper_intercept(FIELD, (-3, 1.5), (-3, -1.5))
        self.assertAlmostEqual(target[0], -6.6)
        self.assertAlmostEqual(target[1], -.3)

    def test_outgoing_wide_slow_old_or_missing_fallback(self):
        for ball, velocity in [(None, (-2, 0)), ((-3, 0), None), ((-3, 0), (2, 0)),
                               ((-3, 0), (-.1, 0)), ((-3, 2), (-2, 0)),
                               ((-7.1, 0), (-2, 0)), ((4, 0), (-1, 0)),
                               ((-3, 0), (math.nan, 0))]:
            self.assertIsNone(keeper_intercept(FIELD, ball, velocity))

    def test_projection_clamps_and_suspends_shuffle(self):
        target = keeper_intercept(FIELD, (-5, 1.2), (-2, 0))
        self.assertEqual(target, (-6.6, 1))
        tracked, direction = keeper_tracking_target(FIELD, (-6.6, 0), (-5, 1.2), 1, (-2, 0))
        self.assertEqual(tracked, target)
        self.assertEqual(direction, 1)

    def test_threat_remains_live_after_nominal_line_crossing(self):
        target = keeper_intercept(FIELD, (-6.8, .5), (-2, -.5))
        self.assertAlmostEqual(target[0], -6.85)
        self.assertAlmostEqual(target[1], .4875)
        tracked, _ = keeper_tracking_target(FIELD, (-6.6, 0), (-6.9, .2), 1, (-2, 0))
        self.assertEqual(tracked, (-6.85, .2))


class KeeperClearTest(unittest.TestCase):
    def test_slow_reachable_front_ball(self):
        self.assertTrue(keeper_can_clear(FIELD, {1: (-6.6, 0)}, (-6.3, .1), (0, 0)))

    def test_rejects_unknown_fast_behind_far_sideways_or_unsafe(self):
        for position, ball, velocity in [((-6.6, 0), (-6.3, 0), None),
                                        ((-6.6, 0), (-6.3, 0), (-2, 0)),
                                        ((-6.6, 0), (-6.8, 0), (0, 0)),
                                        ((-6.6, 0), (-6, .4), (0, 0)),
                                        ((-6.6, 0), (-6.3, .5), (0, 0)),
                                        ((-6.95, 0), (-6.4, 0), (0, 0)),
                                        ((-6.6, 0), (-6.3, math.nan), (0, 0))]:
            self.assertFalse(keeper_can_clear(FIELD, {1: position}, ball, velocity))


class KeeperTraceTest(unittest.TestCase):
    def test_default_off_and_missing_observations_throttled(self):
        context = Context(1, .03, 1, FIELD)
        store = SimpleNamespace()
        out = io.StringIO()
        with redirect_stdout(out):
            tactics.keeper_trace(context, [], store, 'stopped')
        self.assertEqual(out.getvalue(), '')
        with patch.object(tactics, 'KEEPER_TRACE_ENABLED', True), redirect_stdout(out):
            tactics.keeper_trace(context, [], store, 'stopped')
            tactics.keeper_trace(context, [], store, 'stopped')
        self.assertEqual(len(out.getvalue().splitlines()), 1)
        data = json.loads(out.getvalue().split('KEEPER_TRACE ')[1])
        self.assertIsNone(data['ball'])
        self.assertIsNone(data['keeper'])


if __name__ == '__main__':
    unittest.main()
