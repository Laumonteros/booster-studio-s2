"""Pure role, phase and positioning decisions; no SDK or simulator access."""
import math

from .framework.types import GameState, KICKING_TEAM_NONE, SetPlay
from .param import (
    ARRIVE_DIST, ATTACKER_KEEP_DIST_MARGIN_M, KEEPER_ID,
    KEEPER_LINE_MARGIN_M, KEEPER_POST_MARGIN_M,
    KEEPER_BOX_MARGIN_M, KEEPER_RESTART_CLEARANCE_M,
    KEEPER_ACTIVITY_RADIUS_M, KEEPER_SHUFFLE_M, ROAMER_RESTART_WAIT_M,
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
    y = 0.0 if ball is None else ball[1]
    limit = min(field.goal_width / 2 - KEEPER_POST_MARGIN_M, field.goal_area_width / 2 - KEEPER_POST_MARGIN_M)
    y = max(-limit, min(limit, y))
    return -field.length / 2 + KEEPER_LINE_MARGIN_M, max(-limit, min(limit, y + offset))


def keeper_tracking_target(field, position, ball, direction):
    if ball is None or math.dist(position, ball) > KEEPER_ACTIVITY_RADIUS_M:
        return keeper_target(field, ball), direction
    target = keeper_target(field, ball, direction * KEEPER_SHUFFLE_M)
    if math.dist(position, target) <= ARRIVE_DIST:
        direction = -direction
        target = keeper_target(field, ball, direction * KEEPER_SHUFFLE_M)
    return target, direction


def keeper_can_clear(field, positions, ball):
    if ball is None or positions.get(KEEPER_ID) is None:
        return False
    x, y = ball
    in_box = -field.length / 2 <= x <= -field.length / 2 + field.goal_area_length and abs(y) <= field.goal_area_width / 2
    if not in_box:
        return False
    distance = math.dist(positions[KEEPER_ID], ball)
    return all(distance <= math.dist(p, ball) for p in positions.values() if p is not None)


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
