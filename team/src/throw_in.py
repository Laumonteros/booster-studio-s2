"""Short throw-in handoff; receiving waits use a low-speed shuttle."""
import math

from .framework.types import GameState, KICKING_TEAM_NONE, SetPlay
from .throw_in_params import *


def position(player):
    return player.pose.x, player.pose.y


def pass_target(context, origin):
    hx = context.field.length / 2 - FIELD_MARGIN - PATROL_HALF_SPAN
    hy = context.field.width / 2 - FIELD_MARGIN
    x, y = origin
    side = -1 if y >= 0 else 1
    return max(-hx, min(hx, x)), max(-hy, min(hy, y + side * PASS_LENGTH))


def move_receiver(context, player, pending):
    center = pending['target']
    player.action = 'restart:receive_position'
    ball_distance = math.dist(position(player), (context.ball.x, context.ball.y))
    if (not pending['patrolling'] and math.dist(position(player), center) > PATROL_ENTER
            and ball_distance > ACTIVE_RECEIVER_RADIUS):
        player.move_to_position(center)
        return
    pending['patrolling'] = True
    target = center[0] + pending['side'] * PATROL_HALF_SPAN, center[1]
    if math.dist(position(player), target) <= PATROL_ARRIVAL:
        pending['side'] *= -1
        target = center[0] + pending['side'] * PATROL_HALF_SPAN, center[1]
    dx, dy = target[0] - player.pose.x, target[1] - player.pose.y
    length = math.hypot(dx, dy)
    vx, vy = PATROL_SPEED * dx / length, PATROL_SPEED * dy / length
    c, s = math.cos(player.pose.theta), math.sin(player.pose.theta)
    wanted = c * vx + s * vy, -s * vx + c * vy
    old = pending['velocity']
    change = math.dist(wanted, old)
    limit = PATROL_ACCELERATION * max(0., min(context.dt, MAX_CONTROL_DT))
    ratio = min(1., limit / change) if change else 1.
    velocity = tuple(a + (b - a) * ratio for a, b in zip(old, wanted))
    pending['velocity'] = velocity
    player.release_kick()
    player.set_velocity(*velocity, 0.)


def handle(context, players, store):
    game = context.game
    pending = getattr(store, 'throw_in', None)
    if game is None or game.state != GameState.PLAYING or game.stopped:
        store.throw_in = None
        return False
    ours = game.set_play == SetPlay.THROW_IN and game.kicking_team == context.team_id
    if game.kicking_team != KICKING_TEAM_NONE and not ours:
        store.throw_in = None
        return False
    ball = context.ball
    if pending is None and ours and ball is not None and players:
        origin = ball.x, ball.y
        taker = min(players, key=lambda p: math.dist(position(p), origin))
        receiver = next((p for p in players if p.id != taker.id), None)
        pending = dict(origin=origin, taker=taker.id,
                       receiver=receiver.id if receiver else None,
                       target=pass_target(context, origin), stage='pass', contact=None,
                       patrolling=False, side=1, velocity=(0., 0.))
        store.throw_in = pending
    if pending is None:
        return False
    if ball is None:
        for p in players:
            p.stop()
        return True
    taker = next((p for p in players if p.id == pending['taker']), None)
    receiver = next((p for p in players if p.id == pending['receiver']), None)
    if taker is None or receiver is None:
        for p in players:
            p.action = 'restart:missing_partner'
            p.support()
        return True
    b = ball.x, ball.y
    moved = math.dist(b, pending['origin'])
    direction = math.atan2(pending['target'][1] - pending['origin'][1],
                           pending['target'][0] - pending['origin'][0])
    if moved >= HANDOFF_DISTANCE:
        pending['stage'] = 'receive'
    if pending['stage'] == 'pass':
        store.normal_attacker = taker.id
        move_receiver(context, receiver, pending)
        taker.action = 'restart:wait_partner'
        if math.dist(position(receiver), pending['target']) <= RECEIVER_READY:
            taker.action = 'restart:short_pass'
            taker.kick(direction, PASS_POWER)
        else:
            taker.stop()
    else:
        store.normal_attacker = receiver.id
        taker.action = 'support'
        taker.support()
        receiver.action = 'restart:second_touch'
        if moved >= SHOT_DISTANCE:
            receiver.attack()
            if math.dist(position(receiver), b) <= CONTACT_DISTANCE and pending['contact'] is None:
                pending['contact'] = b
            if pending['contact'] is not None and math.dist(b, pending['contact']) >= SECOND_MOVEMENT:
                store.throw_in = None
        else:
            receiver.kick(direction, PASS_POWER)
    return True
