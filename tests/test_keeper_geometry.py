import math
import unittest
from unittest.mock import patch

from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD
from team.src.keeper_geometry import bisector_target, guard_target
import test_team_dispatch as dispatch


class BisectorTest(unittest.TestCase):
    def test_equal_angles_to_posts_and_mirrored_targets(self):
        ball = (-3, 2)
        target = bisector_target(FIELD, ball, .4)
        def angle(point):
            return math.atan2(point[1] - ball[1], point[0] - ball[0])
        def gap(a, b):
            return abs(math.atan2(math.sin(a - b), math.cos(a - b)))
        self.assertAlmostEqual(gap(angle((-7, -1.3)), angle(target)),
                               gap(angle(target), angle((-7, 1.3))))
        self.assertAlmostEqual(target[1], -bisector_target(FIELD, (-3, -2), .4)[1])
        self.assertEqual(bisector_target(FIELD, (-3, 0), .4), (-6.6, 0))

    def test_smooth_depth_retreat_and_post_or_behind_goal(self):
        self.assertAlmostEqual(bisector_target(FIELD, (-6.4, 0), .4)[0], -6.7)
        for ball in [(-7, 1.3), (-7, -1.3), (-8, 2), (-6.99, 6), (-6.99, -6)]:
            x, y = bisector_target(FIELD, ball, .4)
            self.assertGreaterEqual(x, -6.85)
            self.assertLessEqual(x, -6.6)
            self.assertLessEqual(abs(y), 1)

    def test_missing_nonfinite_and_invalid_depth(self):
        for ball in [None, (math.nan, 0), (0, math.inf)]:
            self.assertEqual(bisector_target(FIELD, ball, .4), (-6.6, 0))
            self.assertEqual(guard_target(FIELD, (-6.6, 0), ball, 1, None, .4), ((-6.6, 0), 1, False))
        self.assertEqual(bisector_target(FIELD, (-3, 0), math.nan), (-6.6, 0))
        self.assertAlmostEqual(bisector_target(FIELD, (-3, 0), -1)[0], -6.85)
        self.assertLessEqual(bisector_target(FIELD, (-3, 0), 100)[0], -7 + FIELD.goal_area_length - .05)

    def test_intercept_uses_adjusted_depth_and_no_shuffle(self):
        point, direction, incoming = guard_target(FIELD, (-6.6, 0), (-6.4, .2), -1, (-2, -.5), .4)
        self.assertTrue(incoming)
        self.assertEqual(direction, -1)
        self.assertAlmostEqual(point[0], -6.7)
        self.assertAlmostEqual(point[1], .125)

    def test_wide_outgoing_slow_or_unknown_velocity_tracks(self):
        for ball, velocity in [((-3, 2), (-2, 0)), ((-3, 0), (2, 0)),
                               ((-3, 0), (-.1, 0)), ((-3, 0), None),
                               ((-3, 0), (math.nan, 0)), ((-7.1, 0), (-2, 0))]:
            point, _, incoming = guard_target(FIELD, (-6.6, 0), ball, 1, velocity, .4)
            self.assertFalse(incoming)
            self.assertTrue(all(math.isfinite(v) for v in point))

    def test_post_patrol_preserves_activity_span_and_safe_limits(self):
        first, direction, _ = guard_target(FIELD, (-6.8, -.85), (-6.95, -1.35), -1, None, .4)
        second, _, _ = guard_target(FIELD, first, (-6.95, -1.35), direction, None, .4)
        self.assertAlmostEqual(math.dist(first, second), .7)
        for point in (first, second):
            self.assertLessEqual(abs(point[1]), 1)
            self.assertGreaterEqual(point[0], -6.85)

    def test_far_ball_and_unknown_pose_do_not_patrol(self):
        self.assertEqual(guard_target(FIELD, None, (0, 0), 1, None, .4), ((-6.6, 0), 1, False))
        self.assertEqual(guard_target(FIELD, (-6.6, 0), (0, 0), 1, None, .4), ((-6.6, 0), 1, False))


class KeeperGeometryDispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dispatch.DispatchTest.setUpClass.__func__(cls)

    setUp = dispatch.DispatchTest.setUp
    play = dispatch.DispatchTest.play

    def test_normal_only_routes_keeper_through_bisector(self):
        module = self.Agent.__module__
        with patch(module + '.guard_target', return_value=((-6.7, .2), -1, False)) as guard:
            self.play(ball=(-6.4, .5))
            self.assertEqual(guard.call_count, 1)
            self.assertEqual(self.players[0].calls[-1][1], (-6.7, .2))
            self.assertEqual(self.store.keeper_direction, -1)

    def test_restarts_and_stop_do_not_use_bisector(self):
        from team.src.framework.types import GameState, SetPlay
        with patch(self.Agent.__module__ + '.guard_target', side_effect=AssertionError('normal-only helper')):
            self.play(kicking_team=1, set_play=SetPlay.THROW_IN)
            self.play(ball=(-6.5, 0), kicking_team=2, set_play=SetPlay.THROW_IN)
            self.play(state=GameState.SET)
