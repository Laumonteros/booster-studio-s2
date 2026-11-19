"""Pure role, phase and positioning decisions; no SDK or simulator access."""
import math
import json
import time

from .framework.types import GameState, KICKING_TEAM_NONE, SetPlay
from .param import (
    ARRIVE_DIST, ATTACKER_KEEP_DIST_MARGIN_M, KEEPER_ID,
    KEEPER_LINE_MARGIN_M, KEEPER_POST_MARGIN_M,
    KEEPER_BOX_MARGIN_M, KEEPER_RESTART_CLEARANCE_M,
    KEEPER_ACTIVITY_RADIUS_M, KEEPER_SHUFFLE_M, ROAMER_RESTART_WAIT_M,
    KEEPER_ANGLE_COMPRESSION, KEEPER_SAFE_LINE_MARGIN_M, KEEPER_BACKSTOP_MARGIN_M,
    KEEPER_CLEAR_BALL_DEPTH_M, KEEPER_CLEAR_REACH_M, KEEPER_CLEAR_LATERAL_M,
    KEEPER_CLEAR_SPEED_MPS, KEEPER_INCOMING_MIN_MPS, KEEPER_PREDICT_HORIZON_S,
    KEEPER_VELOCITY_ALPHA, KEEPER_OBSERVATION_MAX_AGE_S,
    KEEPER_TELEPORT_DISTANCE_M, KEEPER_OBSERVATION_MAX_SPEED_MPS,
    KEEPER_STEP_M, KEEPER_TRACE_ENABLED, KEEPER_TRACE_INTERVAL_S,
    OPP_SET_PLAY_CLEARANCE_M, RESTART_PASS_DISTANCE_M, RESTART_PASS_FORWARD_M,
    RESTART_SHOOT_DISTANCE_M, SHOT_POST_MARGIN_M,
    RETREAT_EXTRA_MARGIN_M, RETREAT_FIELD_MARGIN_M, SHOT_GOAL_DEPTH_M,
    SUPPORT_BACK_M, SUPPORT_OFFSET_M, SUPPORT_BOX_MARGIN_M,
    SUPPORT_FIELD_MARGIN_M, SUPPORT_GOAL_MARGIN_M,
)


def phase(context):
    g = context.game
    if g is None or g.stopped:
        return "stopped"
    if g.state == GameState.READY:
        return "ready"
    if g.state != GameState.PLAYING:
        return "stopped"
    if g.kicking_team != KICKING_TEAM_NONE and (
        g.set_play != SetPlay.NONE or g.secondary_time > 0
    ):
        return "our_restart" if g.kicking_team == context.team_id else "their_restart"
    return "normal"


def select_roles(positions, ball, previous=None):
    keeper = KEEPER_ID if positions.get(KEEPER_ID) is not None else None
    roamers = [i for i, p in positions.items() if i != KEEPER_ID and p is not None]
    if ball is None or not roamers:
        return keeper, None, None
    distances = {i: math.dist(positions[i], ball) for i in roamers}
    attacker = min(roamers, key=lambda i: (distances[i], i))
    if previous in distances and distances[previous] <= distances[attacker] + ATTACKER_KEEP_DIST_MARGIN_M:
        attacker = previous
    support = next((i for i in sorted(roamers) if i != attacker), None)
    return keeper, attacker, support


def keeper_target(field, ball, offset=0):
    depth = KEEPER_LINE_MARGIN_M
    if ball is not None and ball[0] < -field.length / 2 + depth:
        depth = KEEPER_BACKSTOP_MARGIN_M
    y = 0.0 if ball is None else ball[1] * KEEPER_ANGLE_COMPRESSION * min(1.0, depth / max(depth, ball[0] + field.length / 2))
    limit = min(field.goal_width / 2 - KEEPER_POST_MARGIN_M, field.goal_area_width / 2 - KEEPER_POST_MARGIN_M)
    y = max(-limit, min(limit, y))
    return -field.length / 2 + depth, max(-limit, min(limit, y + offset))


def keeper_velocity_update(previous, ball, observed_at, now, current):
    if current != "normal" or ball is None or not all(math.isfinite(v) for v in (*ball, observed_at, now)):
        return None
    if not 0 <= now - observed_at <= KEEPER_OBSERVATION_MAX_AGE_S:
        return None
    initial = (ball, observed_at, None)
    if previous is None:
        return initial
    old_ball, old_time, old_velocity = previous
    dt = observed_at - old_time
    if dt == 0:
        return previous if ball == old_ball else initial
    if dt < 0 or dt > KEEPER_OBSERVATION_MAX_AGE_S:
        return initial
    distance = math.dist(ball, old_ball)
    if distance > KEEPER_TELEPORT_DISTANCE_M or distance / dt > KEEPER_OBSERVATION_MAX_SPEED_MPS:
        return initial
    measured = tuple((new - old) / dt for new, old in zip(ball, old_ball))
    if old_velocity is not None:
        measured = tuple(KEEPER_VELOCITY_ALPHA * new + (1 - KEEPER_VELOCITY_ALPHA) * old
                         for new, old in zip(measured, old_velocity))
    return ball, observed_at, measured


def keeper_intercept(field, ball, velocity):
    if ball is None or velocity is None or not all(math.isfinite(v) for v in (*ball, *velocity)):
        return None
    vx, vy = velocity
    line = keeper_target(field, ball)[0]
    if vx >= -KEEPER_INCOMING_MIN_MPS or ball[0] <= -field.length / 2:
        return None
    eta = max(0.0, (line - ball[0]) / vx)
    goal_eta = (-field.length / 2 - ball[0]) / vx
    if eta > KEEPER_PREDICT_HORIZON_S or abs(ball[1] + vy * goal_eta) > field.goal_width / 2:
        return None
    limit = field.goal_width / 2 - KEEPER_POST_MARGIN_M
    return line, max(-limit, min(limit, ball[1] + vy * eta))


def keeper_tracking_target(field, position, ball, direction, velocity=None):
    intercept = keeper_intercept(field, ball, velocity)
    if intercept is not None:
        return intercept, direction
    if ball is None or math.dist(position, ball) > KEEPER_ACTIVITY_RADIUS_M:
        return keeper_target(field, ball), direction
    x, centre = keeper_target(field, ball)
    limit = min(field.goal_width / 2, field.goal_area_width / 2) - KEEPER_POST_MARGIN_M
    centre = max(-limit + KEEPER_SHUFFLE_M, min(limit - KEEPER_SHUFFLE_M, centre))
    target = x, centre + direction * KEEPER_SHUFFLE_M
    if math.dist(position, target) <= ARRIVE_DIST:
        direction = -direction
        target = x, centre + direction * KEEPER_SHUFFLE_M
    return target, direction


def keeper_waypoint(position, target):
    distance = math.dist(position, target)
    ratio = min(1.0, KEEPER_STEP_M / max(distance, 1e-6))
    return tuple(a + (b - a) * ratio for a, b in zip(position, target))


def keeper_can_clear(field, positions, ball, velocity=None):
    if ball is None or positions.get(KEEPER_ID) is None or velocity is None:
        return False
    if not all(math.isfinite(v) for v in (*ball, *velocity, *positions[KEEPER_ID])):
        return False
    if math.hypot(*velocity) > KEEPER_CLEAR_SPEED_MPS or keeper_intercept(field, ball, velocity) is not None:
        return False
    kx, ky = positions[KEEPER_ID]
    if kx <= -field.length / 2 + KEEPER_SAFE_LINE_MARGIN_M:
        return False
    x, y = ball
    in_box = -field.length / 2 + KEEPER_CLEAR_BALL_DEPTH_M <= x <= -field.length / 2 + field.goal_area_length and abs(y) <= field.goal_width / 2 - KEEPER_POST_MARGIN_M
    if not in_box:
        return False
    if x < kx or abs(y - ky) > KEEPER_CLEAR_LATERAL_M:
        return False
    distance = math.dist(positions[KEEPER_ID], ball)
    return distance <= KEEPER_CLEAR_REACH_M and all(distance <= math.dist(p, ball) for p in positions.values() if p is not None)


def keeper_trace(context, players, store, current):
    if not KEEPER_TRACE_ENABLED or context.now - getattr(store, "keeper_trace_at", -math.inf) < KEEPER_TRACE_INTERVAL_S:
        return
    store.keeper_trace_at = context.now
    keeper = next((p for p in players if p.id == KEEPER_ID), None)
    def poses(robots):
        return {i: None if r.pose is None else [r.pose.x, r.pose.y, r.pose.theta] for i, r in robots.items()}
    print("KEEPER_TRACE " + json.dumps({
        "wall_time": time.time(), "now": context.now, "phase": current,
        "remaining": None if context.game is None else context.game.secs_remaining,
        "team_id": context.team_id,
        "ball": None if context.ball is None else [context.ball.x, context.ball.y],
        "ball_seen": None if context.ball is None else context.ball.last_seen_at,
        "teammates": poses(context.teammates), "opponents": poses(context.opponents),
        "velocity": None if getattr(store, "keeper_motion", None) is None else store.keeper_motion[2],
        "target": getattr(store, "keeper_target", None),
        "keeper": None if keeper is None else {
            "branch": getattr(keeper, "action", None), "mode": getattr(keeper, "mode", None),
            "fallen": getattr(keeper, "is_fallen", None), "fall_state": getattr(keeper, "fall_down_state", None),
            "kicking": getattr(keeper, "is_kicking", None), "penalized": keeper.is_penalized,
        },
    }, separators=(",", ":")), flush=True)


def support_target(field, ball):
    bx, by = ball
    y = by - SUPPORT_OFFSET_M if by >= 0 else by + SUPPORT_OFFSET_M
    return (
        max(-field.length / 2 + field.goal_area_length + SUPPORT_BOX_MARGIN_M, min(field.length / 2 - SUPPORT_GOAL_MARGIN_M, bx - SUPPORT_BACK_M)),
        max(-field.width / 2 + SUPPORT_FIELD_MARGIN_M, min(field.width / 2 - SUPPORT_FIELD_MARGIN_M, y)),
    )


def restart_target(field, ball):
    bx, by = ball
    dx = min(RESTART_PASS_FORWARD_M, max(0, field.length / 2 - bx) * RESTART_PASS_DISTANCE_M / (abs(by) + field.goal_width / 2 + SHOT_POST_MARGIN_M))
    return bx + dx, by + (-RESTART_PASS_DISTANCE_M if by >= 0 else RESTART_PASS_DISTANCE_M)


def shot_target(field, ball, origin):
    if origin is not None and math.dist(ball, origin) <= RESTART_SHOOT_DISTANCE_M:
        return restart_target(field, ball)
    side = -1 if ball[1] >= 0 else 1
    return field.length / 2 + SHOT_GOAL_DEPTH_M, side * (field.goal_width / 2 - SHOT_POST_MARGIN_M)


def retreat_target(field, position, ball, keeper=False):
    clearance = OPP_SET_PLAY_CLEARANCE_M if keeper else ROAMER_RESTART_WAIT_M
    if ball is None or math.dist(position, ball) >= clearance:
        return None
    radius = KEEPER_RESTART_CLEARANCE_M if keeper else clearance + ARRIVE_DIST + RETREAT_EXTRA_MARGIN_M
    half_l, half_w = field.length / 2 - RETREAT_FIELD_MARGIN_M, field.width / 2 - RETREAT_FIELD_MARGIN_M
    angle = math.atan2(position[1] - ball[1], position[0] - ball[0])
    candidates = []
    for index in range(72):
        theta = angle + index * math.tau / 72
        point = ball[0] + radius * math.cos(theta), ball[1] + radius * math.sin(theta)
        if abs(point[0]) <= half_l and abs(point[1]) <= half_w:
            if keeper and not (
                -field.length / 2 + KEEPER_BOX_MARGIN_M <= point[0] <= -field.length / 2 + field.goal_area_length - KEEPER_BOX_MARGIN_M
                and abs(point[1]) <= field.goal_area_width / 2 - KEEPER_BOX_MARGIN_M
            ):
                continue
            candidates.append(point)
    return min(candidates, key=lambda p: math.dist(position, p)) if candidates else None
