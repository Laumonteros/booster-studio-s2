"""Clear opponent set plays without rotating into an endline post."""
import math

from .field_params import OPP_SET_PLAY_FIELD_MARGIN_M
from .field_utils import clamp_inside_field
from .framework.types import SetPlay
from .opponent_exit_params import *


def target(context, pose, ball):
    hx = context.field.length / 2 - OPP_SET_PLAY_FIELD_MARGIN_M
    hy = context.field.width / 2 - OPP_SET_PLAY_FIELD_MARGIN_M
    post = context.field.goal_width / 2
    if (context.game is not None and context.game.set_play == SetPlay.GOAL_KICK
            and abs(pose.x) > hx and abs(pose.y) >= post):
        return math.copysign(hx, pose.x), math.copysign(hy, pose.y)
    direction = math.atan2(pose.y - ball.y, pose.x - ball.x)
    points = [(ball.x + EXIT_CLEARANCE * math.cos(direction),
               ball.y + EXIT_CLEARANCE * math.sin(direction))]
    for x in (-hx, hx):
        rest = EXIT_CLEARANCE ** 2 - (x - ball.x) ** 2
        if rest >= 0:
            points.extend((x, ball.y + sign * math.sqrt(rest)) for sign in (-1, 1))
    for y in (-hy, hy):
        rest = EXIT_CLEARANCE ** 2 - (y - ball.y) ** 2
        if rest >= 0:
            points.extend((ball.x + sign * math.sqrt(rest), y) for sign in (-1, 1))
    points = [p for p in points if p == clamp_inside_field(
        context, *p, margin=OPP_SET_PLAY_FIELD_MARGIN_M)]
    return min(points, key=lambda p: math.hypot(p[0] - pose.x, p[1] - pose.y)) if points else None


def clear(context, players):
    ball = context.ball
    for p in players:
        p.action = 'opp_set:wait'
        pose = p.pose
        if ball is None or pose is None or math.hypot(pose.x-ball.x, pose.y-ball.y) >= EXIT_CLEARANCE:
            p.stop()
            continue
        goal = target(context, pose, ball)
        if goal is None:
            p.stop()
            continue
        dx, dy = goal[0]-pose.x, goal[1]-pose.y
        length = math.hypot(dx, dy)
        if length == 0:
            p.stop()
            continue
        vx, vy = EXIT_SPEED*dx/length, EXIT_SPEED*dy/length
        c, s = math.cos(pose.theta), math.sin(pose.theta)
        p.action = 'opp_set:retreat'
        p.release_kick()
        p.set_velocity(c*vx+s*vy, -s*vx+c*vy, 0.)
