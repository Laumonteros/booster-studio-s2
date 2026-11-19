import json
import tempfile
import threading
import queue
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from team.src import telemetry as T
from team.src.player import Player
from team.src.framework.types import Context, ADULT_FIELD_DIMENSIONS as FIELD, BallState, Pose2D


class TelemetryTest(unittest.TestCase):
    def test_off_is_identity_and_does_not_start_writer(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(T.param, 'TELEMETRY_ENABLED', False), patch.object(T, 'writer') as sink:
            self.assertIs(T.instrument_player(Player), Player)
            f = lambda *args: None
            self.assertIs(T.trace_play(f), f)
            sink.assert_not_called()

    def test_writer_flushes_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.jsonl'
            sink = T.Writer(str(path))
            sink.emit({'type': 'test', 'values': [1, None]})
            sink.close()
            self.assertEqual(json.loads(path.read_text()), {'type': 'test', 'values': [1, None]})
            self.assertEqual(sink.dropped, 0)

    def test_writer_error_does_not_raise_in_producer(self):
        with patch('builtins.print'):
            sink = T.Writer('/nonexistent-telemetry-directory/trace.jsonl')
            sink.thread.join(timeout=2)
        sink.emit({'type': 'test'})
        self.assertIsNotNone(sink.error)

    def test_full_queue_never_blocks(self):
        sink = object.__new__(T.Writer)
        sink.queue, sink.dropped = queue.Queue(maxsize=1), 0
        sink.emit(1)
        sink.emit(2)
        self.assertEqual(sink.dropped, 1)

    def test_native_start_stop_pass_through_and_errors(self):
        events = []
        class Manager:
            _kick_active = False
            def start(self):
                self._kick_active = True
                return 17
            def stop(self):
                self._kick_active = False
                raise ValueError('SDK stop failure')
        p = NS(id=2, context=None, pose=None, action='roamer:attack', _trace_local=threading.local())
        T.call_stack(p).extend(['attack', 'kick'])
        probe = T.ManagerProbe(Manager(), p)
        with patch.object(T, 'writer', return_value=NS(emit=events.append)):
            self.assertEqual(probe.start(), 17)
            with self.assertRaisesRegex(ValueError, 'SDK stop failure'):
                probe.stop()
        self.assertEqual([e['type'] for e in events], ['native_start_request','native_start','native_stop_request','native_stop_error'])
        self.assertEqual(events[0]['reason'], 'roamer:attack/attack/kick')

    def test_command_wrapper_preserves_arguments_result_and_exception(self):
        calls = []
        class Base:
            def attack(self, *args, **kwargs):
                calls.append((args, kwargs))
                if kwargs.get('fail'):
                    raise RuntimeError('original')
                return 21
        player = NS(_trace_calls=[], _trace_local=threading.local())
        wrapped = T.trace_method(Base.attack)
        self.assertEqual(wrapped(player, (7, 0), power=4), 21)
        with self.assertRaisesRegex(RuntimeError, 'original'):
            wrapped(player, fail=True)
        self.assertEqual(calls[0], (((7, 0),), {'power':4}))
        self.assertEqual(T.call_stack(player), [])

    def test_backend_probe_retains_velocity_gate_and_exact_kick_args(self):
        class Backend:
            mode = 'walk'
            _kicking = True
            def kick(self, *args):return args
            def set_velocity(self, *args):return args
        p = NS(_trace_commands=[])
        b = T.BackendProbe(Backend(), p)
        self.assertEqual(b.kick(.2, 4, .8, .1), (.2, 4, .8, .1))
        self.assertEqual(b.set_velocity(1, 0, .1), (1, 0, .1))
        self.assertFalse(p._trace_commands[-1]['accepted'])

    def test_empty_roster_and_missing_game_ball_snapshot(self):
        rows = []
        sink = NS(emit=rows.append, dropped=0, error=None)
        with patch.object(T, 'enabled', return_value=True), patch.object(T, 'writer', return_value=sink):
            play = T.trace_play(lambda *args: 9)
        self.assertEqual(play(Context(0,.03,1,FIELD), [], NS(attacker=None)), 9)
        self.assertEqual(rows[0]['players'], [])
        self.assertIsNone(rows[0]['game'])
        self.assertIsNone(rows[0]['ball'])

    def test_enabled_real_player_commands_match_uninstrumented_player(self):
        class Manager:
            _kick_active = False
            def start(self):self._kick_active = True
            def stop(self):self._kick_active = False
        class Backend:
            mode = 'walk'
            _kicking = False
            def __init__(self):
                self._kick_manager, self._worker_stop, self.calls = Manager(), threading.Event(), []
            def kick(self, *args):
                if not self._kicking:self._kick_manager.start()
                self._kicking = True
                self.calls.append(('kick', args))
            def release_kick(self):
                if self._kicking:self._kick_manager.stop()
                self._kicking = False
            def set_velocity(self, *args):self.calls.append(('velocity', args))
        events = []
        sink = NS(emit=events.append, dropped=0, error=None)
        with patch.object(T, 'enabled', return_value=True), patch.object(T, 'writer', return_value=sink):
            traced = T.instrument_player(Player)
            backends = [Backend(), Backend()]
            players = [Player(2, NS(team_id=1), backends[0]), traced(2, NS(team_id=1), None)]
            players[1]._backend = backends[1]
            for x in (-1.0, -1.1, -4.0):
                for p in players:
                    p.context = Context(0,.03,1,FIELD, ball=BallState(0,0),teammates={2:NS(pose=Pose2D(x,0,0))})
                    p.attack((7,0))
            for p in players:p.stop()
        self.assertEqual(backends[0].calls, backends[1].calls)
        self.assertEqual([e['type'] for e in events], ['native_start_request','native_start','native_stop_request','native_stop'])


if __name__ == '__main__':
    unittest.main()
