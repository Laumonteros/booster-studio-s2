import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

from team.src.field_logic import _act_normal, _clear_normal_sticky, _select_closest_attacker


class RoamerHysteresisTest(unittest.TestCase):
    def setUp(self):
        self.context = NS(ball=NS(x=0, y=0))
        self.players = [NS(id=i, pose=NS(x=x, y=0), is_fallen=False,
                           attack=Mock(), support=Mock())
                        for i, x in ((2, 2), (3, 2.5))]
        self.store = NS(normal_attacker=None)

    def assign(self):
        _act_normal(self.context, self.players, self.store)
        return self.store.normal_attacker

    def test_initial_nearest_and_actions(self):
        self.assertEqual(self.assign(), 2)
        self.players[0].attack.assert_called_once_with()
        self.players[1].support.assert_called_once_with()

    def test_keep_within_margin_including_boundary(self):
        self.assign()
        for distance in (1.6, 1.1, 1.0):
            self.players[1].pose.x = distance
            self.assertEqual(self.assign(), 2)

    def test_switch_only_beyond_margin(self):
        self.assign()
        self.players[1].pose.x = .99
        self.assertEqual(self.assign(), 3)
        self.players[0].pose.x = .5
        self.assertEqual(self.assign(), 3)

    def test_unavailable_incumbent_replaced_immediately(self):
        self.assign()
        self.players = self.players[1:]
        self.assertEqual(self.assign(), 3)

    def test_empty_roster(self):
        self.players = []
        self.assertIsNone(self.assign())

    def test_missing_ball_retains_incumbent(self):
        self.assign()
        self.context.ball = None
        self.assertEqual(self.assign(), 2)

    def test_phase_reset_drops_preference(self):
        self.assign()
        _clear_normal_sticky(self.store)
        self.players[1].pose.x = 1.9
        self.assertEqual(self.assign(), 3)

    def test_kickoff_selector_default_unchanged(self):
        self.players[1].pose.x = 1.5
        self.assertEqual(_select_closest_attacker(self.context, self.players, 2).id, 3)


if __name__ == '__main__':
    unittest.main()
