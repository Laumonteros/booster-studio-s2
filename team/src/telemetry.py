"""Opt-in, asynchronous observations of existing commands, not a controller."""
import atexit
import functools
import json
import os
import queue
import threading
import time

from . import param


def enabled():
    return param.TELEMETRY_ENABLED or bool(os.environ.get('ROAMER_TELEMETRY_FILE'))


class Writer:
    def __init__(self, path):
        self.path = path
        self.queue = queue.Queue(maxsize=4096)
        self.dropped = 0
        self.error = None
        self.thread = threading.Thread(target=self.run, name='telemetry-writer', daemon=True)
        self.thread.start()

    def emit(self, row):
        try:
            self.queue.put_nowait(row)
        except queue.Full:
            self.dropped += 1

    def run(self):
        try:
            with open(self.path, 'a', buffering=65536) as output:
                while True:
                    try:
                        row = self.queue.get(timeout=0.5)
                    except queue.Empty:
                        output.flush()
                        continue
                    if row is None:
                        output.flush()
                        return
                    try:
                        output.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
                    except (TypeError, ValueError):
                        self.dropped += 1
                    if self.queue.empty():
                        output.flush()
        except Exception as exc:
            self.error = repr(exc)
            print('TELEMETRY_WRITER_ERROR ' + self.error, flush=True)

    def close(self):
        try:
            self.queue.put(None, timeout=1)
        except queue.Full:
            return
        self.thread.join(timeout=2)


_writer = None


def writer():
    global _writer
    if _writer is None:
        _writer = Writer(os.environ.get('ROAMER_TELEMETRY_FILE', '/tmp/roamer-telemetry.jsonl'))
        atexit.register(_writer.close)
    return _writer


def pose_tuple(pose):
    return None if pose is None else (pose.x, pose.y, pose.theta)


def call_stack(player):
    local = player._trace_local
    if not hasattr(local, 'stack'):
        local.stack = []
    return local.stack


def reason(player):
    stack = '/'.join(call_stack(player))
    if not stack:
        backend = player._backend
        return 'backend:shutdown' if backend._worker_stop.is_set() else 'backend:mode_or_recovery'
    return player.action + '/' + stack


class ManagerProbe:
    def __init__(self, manager, player):
        self.manager, self.player = manager, player

    def __getattr__(self, name):
        return getattr(self.manager, name)

    def event(self, kind, **extra):
        p = self.player
        ctx = p.context
        writer().emit(dict(type=kind, wall=time.time(), now=None if ctx is None else ctx.now,
                           robot=p.id, thread=threading.current_thread().name,
                           reason=reason(p), pose=pose_tuple(p.pose),
                           ball=None if ctx is None or ctx.ball is None else (ctx.ball.x, ctx.ball.y),
                           action=p.action, **extra))

    def call(self, name):
        self.event('native_' + name + '_request', active_before=getattr(self.manager, '_kick_active', None))
        try:
            result = getattr(self.manager, name)()
        except Exception as exc:
            self.event('native_' + name + '_error', error=repr(exc))
            raise
        self.event('native_' + name, active_after=getattr(self.manager, '_kick_active', None))
        return result

    def start(self):
        return self.call('start')

    def stop(self):
        return self.call('stop')


class BackendProbe:
    def __init__(self, backend, player):
        self.backend, self.player = backend, player

    def __getattr__(self, name):
        return getattr(self.backend, name)

    def kick(self, direction, power, ball_x, ball_y):
        self.player._trace_commands.append(dict(kind='kick_body', direction=direction, power=power,
                                               ball=(ball_x, ball_y), mode=self.backend.mode))
        return self.backend.kick(direction, power, ball_x, ball_y)

    def set_velocity(self, vx, vy, vyaw):
        self.player._trace_commands.append(dict(kind='velocity_body', velocity=(vx, vy, vyaw),
                                               accepted=self.backend.mode == 'walk' and not self.backend._kicking))
        return self.backend.set_velocity(vx, vy, vyaw)


def trace_method(method):
    @functools.wraps(method)
    def traced(self, *args, **kwargs):
        self._trace_calls.append(dict(method=method.__name__, args=args, kwargs=dict(kwargs)))
        stack = call_stack(self)
        stack.append(method.__name__)
        try:
            return method(self, *args, **kwargs)
        finally:
            stack.pop()
    return traced


def instrument_player(base):
    if not enabled():
        return base
    writer()

    class TracedPlayer(base):
        def __init__(self, *args, **kwargs):
            self._trace_local = threading.local()
            self._trace_calls, self._trace_commands = [], []
            super().__init__(*args, **kwargs)

        def __setattr__(self, name, value):
            if name == '_backend' and value is not None and not isinstance(value, BackendProbe):
                value._kick_manager = ManagerProbe(value._kick_manager, self)
                value = BackendProbe(value, self)
            super().__setattr__(name, value)

    for name in ('attack', 'walk_to', 'move_to_position', 'stop', 'kick', 'release_kick'):
        setattr(TracedPlayer, name, trace_method(getattr(base, name)))
    return TracedPlayer


def trace_play(play):
    if not enabled():
        return play
    sink = writer()

    @functools.wraps(play)
    def traced(context, players, store):
        start = time.time()
        for player in players:
            player._trace_calls, player._trace_commands = [], []
        try:
            return play(context, players, store)
        finally:
            game, ball = context.game, context.ball
            sink.emit(dict(
                type='tick', wall=start, wall_end=time.time(), now=context.now, dt=context.dt,
                team=context.team_id, dropped=sink.dropped, writer_error=sink.error,
                game=None if game is None else dict(state=game.state.name, set_play=game.set_play.name,
                    kicking_team=game.kicking_team, stopped=game.stopped, remaining=game.secs_remaining,
                    secondary=game.secondary_time),
                ball=None if ball is None else (ball.x, ball.y),
                ball_seen=None if ball is None else ball.last_seen_at,
                opponents={i: pose_tuple(r.pose) for i, r in context.opponents.items()},
                players=[dict(id=p.id, role='keeper' if p.id == 1 else 'attacker' if p.id == store.attacker else 'support',
                    action=p.action, pose=pose_tuple(p.pose), kicking=getattr(p, 'is_kicking', None),
                    native_active=None if getattr(p, '_backend', None) is None else getattr(p._backend._kick_manager, '_kick_active', None),
                    calls=p._trace_calls, commands=p._trace_commands) for p in players],
            ))
    return traced
