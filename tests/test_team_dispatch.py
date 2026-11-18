"""Exercise real play dispatch with SDK-free fake action handles."""
import importlib
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context,
    GameControlState, GameState, Pose2D, SetPlay,
)


class FakePlayer:
    def __init__(self, player_id, pose):
        self.id = player_id
        self.pose = Pose2D(*pose) if pose is not None else None
        self.is_penalized = False
        self.ready = True
        self.calls = []

    def ensure_ready(self):
        return self.ready

    def stop(self):
        self.calls.append(('stop',))

    def walk_to(self, target, **kwargs):
        self.calls.append(('walk', target, kwargs))

    def move_to_position(self, target):
        self.calls.append(('support', target))

    def attack(self, target, **kwargs):
        self.calls.append(('attack', target, kwargs))


class DispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sdk = ModuleType('booster_agent_framework')
        sdk.AgentBase = type('AgentBase', (), {})
        mixin = ModuleType('team.src.framework.agent')
        mixin.SoccerAgentMixin = type('SoccerAgentMixin', (), {})
        with patch.dict(sys.modules, {'booster_agent_framework': sdk, 'team.src.framework.agent': mixin}):
            cls.Agent = importlib.import_module('team.src.main').SoccerSimAgent

    def setUp(self):
        self.players = [FakePlayer(1, (-6.6, 0, 0)), FakePlayer(2, (-1, 0, 0)), FakePlayer(3, (-4, 2, 0))]
        self.store = SimpleNamespace()
        self.Agent().init_store(self.store)

    def play(self, state=GameState.PLAYING, ball=(0, 0), **kwargs):
        context = Context(0, .03, 1, FIELD, game=GameControlState(state=state, **kwargs), ball=BallState(*ball) if ball is not None else None)
        self.Agent.play(context, self.players, self.store)

    def test_normal_fixed_keeper_and_two_roamers(self):
        self.play()
        self.assertEqual([p.calls[-1][0] for p in self.players], ['walk', 'attack', 'support'])
        self.assertAlmostEqual(self.players[0].calls[-1][1][0], -6.6)

    def test_set_and_stop_never_attempt_recovery(self):
        for player in self.players:
            player.ensure_ready = lambda: self.fail('SET/STOP must not start recovery')
        self.play(state=GameState.SET)
        self.play(stopped=True)
        for player in self.players:
            self.assertEqual(player.calls, [('stop',), ('stop',)])

    def test_empty_roster(self):
        self.players = []
        self.play()
        self.assertIsNone(self.store.attacker)

    def test_missing_ball_stops_roamers(self):
        self.play(ball=None)
        self.assertEqual([p.calls[-1][0] for p in self.players], ['walk', 'stop', 'stop'])

    def test_ineligible_players_excluded(self):
        self.players[1].is_penalized = True
        self.players[2].ready = False
        self.play()
        self.assertIsNone(self.store.attacker)
        self.assertEqual([p.calls[-1][0] for p in self.players], ['walk', 'stop', 'stop'])

    def test_unknown_pose_stops(self):
        self.players[1].pose = None
        self.play()
        self.assertEqual(self.store.attacker, 3)
        self.assertEqual(self.players[1].calls[-1], ('stop',))

    def test_keeper_clears_and_roamers_space_out(self):
        self.play(ball=(-6.5, 0))
        self.assertEqual([p.calls[-1][0] for p in self.players], ['attack', 'support', 'support'])
        targets = [p.calls[-1][1] for p in self.players[1:]]
        self.assertNotEqual(targets[0], targets[1])

    def test_opponent_restart_clear_players_stop(self):
        self.players[1].pose = Pose2D(-4, 0, 0)
        self.play(kicking_team=2, set_play=SetPlay.THROW_IN)
        self.assertTrue(all(p.calls[-1] == ('stop',) for p in self.players))

    def test_opponent_restart_near_keeper_stays_in_box(self):
        self.play(ball=(-6.5, 0), kicking_team=2, set_play=SetPlay.THROW_IN)
        action, target, _ = self.players[0].calls[-1]
        self.assertEqual(action, 'walk')
        self.assertLessEqual(target[0], -7 + FIELD.goal_area_length)
        self.assertGreaterEqual(target[0], -7)

    def test_restart_origin_persists_after_referee_releases(self):
        self.play(kicking_team=1, secondary_time=10)
        self.assertEqual(self.players[1].calls[-1][2]['power'], 1.5)
        self.play(ball=(.4, 0))
        self.assertEqual(self.store.restart_origin, (0, 0))
        self.assertEqual(self.players[1].calls[-1][2]['power'], 1.5)
        self.play(ball=(1.5, 0))
        self.assertEqual(self.players[1].calls[-1], ('stop',))
        self.play(ball=(1.5, 0))
        self.assertIsNone(self.players[1].calls[-1][2]['power'])
        self.assertGreater(self.players[1].calls[-1][1][0], 7)

    def test_restart_taker_locked_until_release(self):
        self.play(kicking_team=1, secondary_time=10)
        self.players[2].pose = Pose2D(0, 0, 0)
        self.players[1].pose = Pose2D(-1.4, 0, 0)
        self.play(kicking_team=1, secondary_time=9)
        self.assertEqual(self.store.attacker, 2)
        self.play()
        self.assertEqual(self.store.attacker, 3)


if __name__ == '__main__':
    unittest.main()
