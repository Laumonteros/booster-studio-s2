"""Field-only restart handoff, radial clearance and inactivity safeguards."""
import math

from .framework.types import GameState, KICKING_TEAM_NONE
from .field_safety_params import *


def point(p):
    return p.pose.x, p.pose.y


def bounded(context, target):
    x,y=target
    hx=context.field.length/2-SAFETY_FIELD_MARGIN
    hy=context.field.width/2-SAFETY_FIELD_MARGIN
    return max(-hx,min(hx,x)),max(-hy,min(hy,y))


def radial_target(context, pose, ball, radius):
    dx,dy=pose[0]-ball[0],pose[1]-ball[1]
    d=math.hypot(dx,dy)
    ux,uy=(dx/d,dy/d) if d else (-1.,0.)
    candidates=[(ball[0]+ux*radius,ball[1]+uy*radius)]
    hx=context.field.length/2-SAFETY_FIELD_MARGIN
    hy=context.field.width/2-SAFETY_FIELD_MARGIN
    for x in (-hx,hx):
        r=radius**2-(x-ball[0])**2
        if r>=0:
            candidates.extend((x,ball[1]+sign*math.sqrt(r))for sign in (-1,1))
    for y in (-hy,hy):
        r=radius**2-(y-ball[1])**2
        if r>=0:
            candidates.extend((ball[0]+sign*math.sqrt(r),y)for sign in (-1,1))
    valid=[t for t in candidates if abs(t[0])<=hx+1e-8 and abs(t[1])<=hy+1e-8]
    return min(valid,key=lambda t:math.dist(pose,t)) if valid else bounded(context,pose)


def move_direct(p, target, speed):
    p.release_kick()
    dx,dy=target[0]-p.pose.x,target[1]-p.pose.y
    distance=math.hypot(dx,dy)
    if distance<0.05:
        p.stop()
        return
    vx,vy=speed*dx/distance,speed*dy/distance
    c,s=math.cos(p.pose.theta),math.sin(p.pose.theta)
    p.set_velocity(c*vx+s*vy,-s*vx+c*vy,0.)


def clear_opponent(context, players):
    ball=context.ball
    for p in players:
        p.action='opp_set:wait'
        if ball is None or p.pose is None:
            p.stop()
            continue
        b=ball.x,ball.y
        if math.dist(point(p),b)>=RESTART_CLEARANCE:
            p.stop()
        else:
            p.action='opp_set:radial_exit'
            move_direct(p,radial_target(context,point(p),b,RESTART_CLEARANCE+0.1),EXIT_SPEED)


def support(context, p, store):
    ball=context.ball
    if ball is None or p.pose is None:
        p.stop()
        return
    memory=getattr(store,'support_memory',{})
    store.support_memory=memory
    b=ball.x,ball.y
    old=memory.get(p.id)
    if old is None or (not old['escape'] and math.dist(point(p),old['pose'])>SUPPORT_MOVEMENT) or math.dist(b,old['ball'])>SUPPORT_BALL_MOVEMENT:
        old=dict(pose=point(p),ball=b,since=context.now,escape=False)
        memory[p.id]=old
    if math.dist(point(p),b)<INACTIVITY_RADIUS and context.now-old['since']>=SUPPORT_STILL_SECONDS:
        old['escape']=True
    if old['escape']:
        p.action='support:inactive_escape'
        target=radial_target(context,point(p),b,SUPPORT_WAIT_RADIUS)
        if math.dist(point(p),b)<SUPPORT_WAIT_RADIUS-0.1:
            move_direct(p,target,SUPPORT_ESCAPE_SPEED)
        else:
            p.stop()
    else:
        p.support()


def restart(context, players, store, phase):
    g=context.game
    pending=getattr(store,'restart_pass',None)
    if g is None or g.state!=GameState.PLAYING:
        store.restart_pass=None
        return False
    if g.kicking_team not in (context.team_id,KICKING_TEAM_NONE):
        store.restart_pass=None
        return False
    ours=phase in ('our_kickoff','our_set_play')
    entering=ours and getattr(store,'last_safety_phase',None)!=phase
    store.last_safety_phase=phase
    if entering:
        pending=None
        store.restart_pass=None
    if g.stopped:
        return False
    ball=context.ball
    if pending is None and ours and ball is not None and players:
        taker=min(players,key=lambda p:math.dist(point(p),(ball.x,ball.y)))
        receiver=next((p for p in players if p.id!=taker.id),None)
        sign=-1 if ball.y>=0 else 1
        target=bounded(context,(ball.x+RESTART_PASS_ADVANCE,ball.y+sign*RESTART_PASS_LENGTH))
        pending=dict(origin=(ball.x,ball.y),taker=taker.id,receiver=receiver.id if receiver else None,
                     target=target,stage='pass',contact=None)
        store.restart_pass=pending
    store.restart_phase=phase if ours else getattr(store,'restart_phase',None)
    if pending is None:
        return False
    if ball is None:
        for p in players:p.stop()
        return True
    b=ball.x,ball.y
    taker=next((p for p in players if p.id==pending['taker']),None)
    receiver=next((p for p in players if p.id==pending['receiver']),None)
    if receiver is None or taker is None:
        for p in players:
            p.action='restart:missing_partner'
            support(context,p,store)
        return True
    store.normal_attacker=taker.id
    if phase=='our_kickoff':
        store.kickoff_taker=taker.id
    moved=math.dist(b,pending['origin'])
    if moved>=RESTART_HANDOFF_DISTANCE:
        pending['stage']='receive'
    if pending['stage']=='pass':
        receiver.action='restart:receive_position'
        receiver.move_to_position(pending['target'])
        taker.action='restart:wait_partner'
        if math.dist(point(receiver),pending['target'])<=RESTART_RECEIVER_READY:
            taker.action='restart:short_pass'
            ox,oy=pending['origin'];tx,ty=pending['target']
            taker.kick(math.atan2(ty-oy,tx-ox),RESTART_PASS_POWER)
        else:taker.stop()
    else:
        taker.action='support'
        support(context,taker,store)
        receiver.action='restart:second_touch'
        store.normal_attacker=receiver.id
        if moved>=RESTART_SHOT_DISTANCE:
            receiver.attack()
            if math.dist(point(receiver),b)<=RESTART_CONTACT_DISTANCE:
                if pending['contact'] is None:pending['contact']=b
            if pending['contact'] is not None and math.dist(b,pending['contact'])>=RESTART_SECOND_MOVEMENT:
                store.restart_pass=None
        else:
            ox,oy=pending['origin'];tx,ty=pending['target']
            receiver.kick(math.atan2(ty-oy,tx-ox),RESTART_PASS_POWER)
    return True
