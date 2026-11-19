"""Normal-play second-ball positioning with a pose-based inactivity escape."""
import math

from .framework.types import GameState, KICKING_TEAM_NONE, SetPlay
from .field_params import GOAL_TARGET_DEPTH_M
from .rebound_params import *


def bounded(context, point):
    hx = context.field.length/2-FIELD_MARGIN_M
    hy = context.field.width/2-FIELD_MARGIN_M
    return max(-hx,min(hx,point[0])), max(-hy,min(hy,point[1]))


def position(player):
    return player.pose.x, player.pose.y


def target(context, player, attacker, patrol=0., span=FLANK_M):
    ball = context.ball
    dx, dy = context.field.length/2-ball.x, -ball.y
    length = max(math.hypot(dx,dy),1e-6)
    ux, uy = dx/length, dy/length
    along = TRAIL_M-(TRAIL_M+GOALWARD_M)*max(0.,min(1.,ball.x/TRANSITION_M))+patrol
    origin = position(player)
    shot_y = getattr(attacker,'_normal_shot_y',0.)
    shot_x = context.field.length/2+(GOAL_TARGET_DEPTH_M if shot_y==0 else 0.)
    sx, sy = shot_x-ball.x, shot_y-ball.y
    shot_length = max(math.hypot(sx,sy),1e-6)
    candidates = {}
    for side in (-1,1):
        point = bounded(context,(ball.x-along*ux-side*span*uy,
                                 ball.y-along*uy+side*span*ux))
        lateral = (point[0]-ball.x)*(-uy)+(point[1]-ball.y)*ux
        valid = side*lateral>=LANE_MARGIN_M
        projection = ((point[0]-ball.x)*sx+(point[1]-ball.y)*sy)/(shot_length*shot_length)
        if 0<projection<1:
            valid = valid and abs((point[0]-ball.x)*sy-(point[1]-ball.y)*sx)/shot_length>=LANE_MARGIN_M
        if attacker.pose is not None:
            valid = valid and math.dist(point,position(attacker))>=PARTNER_MARGIN_M
        candidates[side] = point, valid
    if not any(valid for point,valid in candidates.values()) and along<TRAIL_M-1e-6:
        return target(context,player,attacker,patrol+TRAIL_M-along,span)
    if not any(valid for point,valid in candidates.values()) and span<2*FLANK_M:
        return target(context,player,attacker,patrol,2*FLANK_M)
    previous = getattr(player,'_rebound_side',None)
    if previous in candidates and candidates[previous][1]:
        side = previous
    else:
        side = min(candidates,key=lambda s:(not candidates[s][1],math.dist(origin,candidates[s][0])))
    player._rebound_side = side
    return candidates[side][0]


def escape_target(context, player):
    ball = context.ball
    angle = math.atan2(player.pose.y-ball.y,player.pose.x-ball.x)
    points = [bounded(context,(ball.x+ESCAPE_RADIUS_M*math.cos(angle+a),
                               ball.y+ESCAPE_RADIUS_M*math.sin(angle+a)))
              for a in (0.,math.pi/4,-math.pi/4,math.pi/2,-math.pi/2,math.pi)]
    return min(points,key=lambda p:(math.dist(p,(ball.x,ball.y))<ESCAPE_RADIUS_M-.1,
                                    math.dist(p,position(player))))


def handle(context, player, attacker):
    game, ball = context.game, context.ball
    if (player.id==1 or player.pose is None or ball is None or game is None
            or game.state!=GameState.PLAYING or game.stopped or game.set_play!=SetPlay.NONE
            or game.kicking_team!=KICKING_TEAM_NONE or game.secondary_time>0):
        return False
    now, here = context.now, position(player)
    previous = getattr(player,'_rebound_seen',None)
    if previous is None or now-previous>OBSERVATION_GAP_S:
        player._rebound_anchor = now, here
        player._rebound_escape = None
        player._rebound_epoch = now
    player._rebound_seen = now
    anchor_time, anchor = player._rebound_anchor
    if math.dist(anchor,here)>=PROGRESS_M:
        player._rebound_anchor = now, here
        anchor_time = now
    escaping = player._rebound_escape
    gap = math.dist(here,(ball.x,ball.y))
    if escaping is not None:
        origin, point = escaping
        if math.dist(here,origin)>=ESCAPE_PROGRESS_M or gap>=INACTIVITY_RADIUS_M+.1:
            player._rebound_escape = None
        else:
            player.action = 'support:escape'
            player.move_to_position(point)
            return True
    if now-anchor_time>=STALL_S and gap<INACTIVITY_RADIUS_M:
        point = escape_target(context,player)
        player._rebound_escape = here, point
        player.action = 'support:escape'
        player.move_to_position(point)
        return True
    center = target(context,player,attacker)
    patrol = PATROL_SPAN_M*math.sin(math.tau*(now-player._rebound_epoch)/PATROL_PERIOD_S)
    point = target(context,player,attacker,patrol)
    player.action = 'support:rebound'
    if math.dist(here,center)<=LOCAL_RADIUS_M:
        distance = math.dist(here,point)
        scale = min(1.,LOCAL_STEP_M/max(distance,1e-6))
        step = here[0]+(point[0]-here[0])*scale, here[1]+(point[1]-here[1])*scale
        player.walk_to(step,face=player.pose.theta,avoid_ball=True,avoid_robots=True,
                       arrive_dist=LOCAL_ARRIVAL_M)
    else:
        player.move_to_position(center)
    return True
