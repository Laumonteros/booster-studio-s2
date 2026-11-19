"""Normal-play goal-mouth selection without changing native task ownership."""
import math

from .field_shooting_params import (
    SHOT_LANE_RADIUS, SHOT_POST_MARGIN, SHOT_RANGE, SHOT_SWITCH_MARGIN,
)
from .framework.types import GameState, KICKING_TEAM_NONE, SetPlay
from .field_utils.geom import opponent_goal


def clearance(ball, target, opponents):
    dx, dy = target[0]-ball.x, target[1]-ball.y
    length2 = dx*dx+dy*dy
    if length2 <= 1e-9:
        return 0.
    gaps = []
    for state in opponents.values():
        pose = state.pose
        if pose is None:
            continue
        t = ((pose.x-ball.x)*dx+(pose.y-ball.y)*dy)/length2
        if 0 < t <= 1:
            gaps.append(math.hypot(pose.x-ball.x-t*dx, pose.y-ball.y-t*dy))
    return min(gaps, default=math.inf)


def shot_target(player):
    context = player.context
    if player.id==1 or player.action!='attack' or context is None or player.pose is None:
        return None
    game, ball = context.game, context.ball
    if (game is None or ball is None or game.state!=GameState.PLAYING or game.stopped
            or game.set_play!=SetPlay.NONE or game.kicking_team!=KICKING_TEAM_NONE
            or game.secondary_time>0):
        return None
    goal_x = context.field.length/2
    if ball.x>=goal_x or math.hypot(goal_x-ball.x,ball.y)>SHOT_RANGE:
        player._normal_shot_y = 0.
        return None
    side_y = max(0., context.field.goal_width/2-SHOT_POST_MARGIN)
    center = opponent_goal(context)
    center_y = ball.y+(goal_x-ball.x)*(center[1]-ball.y)/(center[0]-ball.x)
    targets = [center, (goal_x,-side_y), (goal_x,side_y)]
    endpoints = [(goal_x,center_y), *targets[1:]]
    scores = [clearance(ball,t,context.opponents) for t in endpoints]
    previous = getattr(player,'_normal_shot_y',0.)
    current = next((i for i,t in enumerate(targets) if t[1]==previous),0)
    best = max(range(len(targets)),key=lambda i:scores[i])
    if scores[0]>=SHOT_LANE_RADIUS+SHOT_SWITCH_MARGIN or (current==0 and scores[0]>=SHOT_LANE_RADIUS):
        chosen = 0
    elif (scores[best]>=SHOT_LANE_RADIUS>scores[current]
          or scores[best]>scores[current]+SHOT_SWITCH_MARGIN):
        chosen = best
    else:
        chosen = current
    player._normal_shot_y = targets[chosen][1]
    return targets[chosen]
