"""Limit normal attacking chassis speed only in close robot traffic."""
import math

from .field_motion_params import CLOSE_RADIUS, CLOSE_SPEED, CROWD_RADIUS
from .field_params import MAX_LINEAR
from .framework.types import GameState, KICKING_TEAM_NONE, SetPlay


def limit_velocity(player, vx, vy, vyaw):
    original = vx, vy, vyaw
    context = player.context
    if player.id == 1 or player.action != 'attack' or context is None:
        return original
    game, pose = context.game, player.pose
    if (game is None or pose is None or game.state != GameState.PLAYING or game.stopped
            or game.set_play != SetPlay.NONE or game.kicking_team != KICKING_TEAM_NONE
            or game.secondary_time > 0):
        return original
    speed = math.hypot(vx, vy)
    if speed <= CLOSE_SPEED:
        return original
    others = [state.pose for rid, state in context.teammates.items()
              if rid != player.id and state.pose is not None]
    others.extend(state.pose for state in context.opponents.values() if state.pose is not None)
    nearest = min((math.hypot(p.x-pose.x, p.y-pose.y) for p in others), default=math.inf)
    if nearest >= CROWD_RADIUS:
        return original
    fraction = max(0., (nearest-CLOSE_RADIUS)/(CROWD_RADIUS-CLOSE_RADIUS))
    limit = CLOSE_SPEED + (MAX_LINEAR-CLOSE_SPEED)*fraction
    if speed <= limit:
        return original
    ratio = limit/speed
    return vx*ratio, vy*ratio, vyaw
