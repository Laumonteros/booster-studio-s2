"""Keeper-only goal-angle geometry."""
import math

from .param import (
    ARRIVE_DIST, KEEPER_ACTIVITY_RADIUS_M, KEEPER_BACKSTOP_MARGIN_M,
    KEEPER_BALL_STANDOFF_M, KEEPER_BOX_MARGIN_M, KEEPER_INCOMING_MIN_MPS, KEEPER_LINE_MARGIN_M,
    KEEPER_POST_MARGIN_M, KEEPER_PREDICT_HORIZON_S, KEEPER_SHUFFLE_M,
)


def bisector_target(field, ball, depth):
    goal = -field.length / 2
    if ball is None or not all(math.isfinite(v) for v in ball):
        return goal + KEEPER_LINE_MARGIN_M, 0.0
    bx, by = ball
    if not math.isfinite(depth):
        depth = KEEPER_LINE_MARGIN_M
    depth = max(KEEPER_BACKSTOP_MARGIN_M, min(depth, field.goal_area_length - KEEPER_BOX_MARGIN_M,
                                           bx - goal - KEEPER_BALL_STANDOFF_M))
    x = goal + depth
    vectors = [(goal - bx, post - by) for post in (-field.goal_width / 2, field.goal_width / 2)]
    lengths = [math.hypot(*v) for v in vectors]
    limit = min(field.goal_width, field.goal_area_width) / 2 - KEEPER_POST_MARGIN_M
    y = by
    if bx > goal and min(lengths) > 1e-9:
        ux, uy = (sum(v[i] / length for v, length in zip(vectors, lengths)) for i in (0, 1))
        if abs(ux) > 1e-9:
            y += (x - bx) * uy / ux
    return x, max(-limit, min(limit, y))


def guard_target(field, position, ball, direction, velocity, depth):
    if ball is None or not all(math.isfinite(v) for v in ball):
        return bisector_target(field, None, depth), direction, False
    active = position is not None and all(math.isfinite(v) for v in position) and math.dist(position, ball) <= KEEPER_ACTIVITY_RADIUS_M
    if not active:
        depth = KEEPER_LINE_MARGIN_M
    target = bisector_target(field, ball, depth)
    if ball is not None and velocity is not None and all(math.isfinite(v) for v in (*ball, *velocity)):
        vx, vy = velocity
        if vx < -KEEPER_INCOMING_MIN_MPS and ball[0] > -field.length / 2:
            eta = max(0.0, (target[0] - ball[0]) / vx)
            goal_eta = (-field.length / 2 - ball[0]) / vx
            if eta <= KEEPER_PREDICT_HORIZON_S and abs(ball[1] + vy * goal_eta) <= field.goal_width / 2:
                limit = field.goal_width / 2 - KEEPER_POST_MARGIN_M
                return (target[0], max(-limit, min(limit, ball[1] + vy * eta))), direction, True
    if not active:
        return target, direction, False
    limit = min(field.goal_width, field.goal_area_width) / 2 - KEEPER_POST_MARGIN_M
    centre = max(-limit + KEEPER_SHUFFLE_M, min(limit - KEEPER_SHUFFLE_M, target[1]))
    destination = target[0], centre + direction * KEEPER_SHUFFLE_M
    if math.dist(position, destination) <= ARRIVE_DIST:
        direction = -direction
        destination = target[0], centre + direction * KEEPER_SHUFFLE_M
    return destination, direction, False
