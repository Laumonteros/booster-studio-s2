"""One fixed deep keeper and two roaming attackers."""
import math

from booster_agent_framework import AgentBase

from .framework.agent import SoccerAgentMixin
from .framework import debugdraw
from .param import (
    KEEPER_ID, OMNI_DIST, READY_TAKER_POSITION, READY_WAITING_POSITIONS,
    RESTART_PASS_POWER, RESTART_SHOOT_DISTANCE_M,
)
from .player import Player
from .tactics import (
    keeper_can_clear, keeper_target, keeper_tracking_target, phase, retreat_target,
    keeper_velocity_update, keeper_intercept, keeper_waypoint, keeper_trace,
    select_roles, shot_target, support_target,
)


class SoccerSimAgent(SoccerAgentMixin, AgentBase):
    player_class = Player

    def init_store(self, store):
        store.attacker = None
        store.phase = None
        store.restart_origin = None
        store.restart_taker = None
        store.keeper_direction = 1

    @staticmethod
    def play(context, players, store):
        current = phase(context)
        ball = (context.ball.x, context.ball.y) if context.ball is not None else None
        store.keeper_motion = keeper_velocity_update(
            getattr(store, "keeper_motion", None), ball,
            context.ball.last_seen_at if context.ball is not None else context.now, context.now, current,
        )
        keeper_velocity = None if store.keeper_motion is None else store.keeper_motion[2]
        store.keeper_target = None
        if current == "stopped":
            for player in players:
                player.action = "stopped"
                player.stop()
            store.phase = current
            keeper_trace(context, players, store, current)
            return

        active = []
        for player in players:
            if player.is_penalized:
                player.action = "penalized"
                player.stop()
            elif not player.ensure_ready() or player.pose is None:
                player.action = "recovering"
                player.stop()
            else:
                active.append(player)
        positions = {p.id: (p.pose.x, p.pose.y) for p in active}
        keeper, attacker, support = select_roles(positions, ball, store.attacker)
        store.attacker = attacker

        if current == "their_restart":
            store.restart_origin = None
            for player in active:
                target = retreat_target(context.field, positions[player.id], ball, keeper=player.id == KEEPER_ID)
                player.action = "restart:clearance"
                if target is None:
                    player.stop()
                else:
                    x, y = positions[player.id]
                    distance = math.dist((x, y), target)
                    ratio = min(1.0, OMNI_DIST / (2 * max(distance, 1e-6)))
                    step = x + (target[0] - x) * ratio, y + (target[1] - y) * ratio
                    player.walk_to(step, face=player.pose.theta)
        elif current == "ready":
            store.restart_origin = None
            for player in active:
                target = keeper_target(context.field, None) if player.id == KEEPER_ID else (
                    READY_TAKER_POSITION if player.id == 2 and context.game.kicking_team == context.team_id
                    else READY_WAITING_POSITIONS[player.id]
                )
                player.action = "ready"
                player.walk_to(target, face=0.0, avoid_ball=True, avoid_robots=True)
        else:
            if current == "our_restart" and store.phase != "our_restart":
                store.restart_origin = ball
                store.restart_taker = attacker
            if current == "our_restart" and store.restart_origin is None:
                store.restart_origin = ball
            if current == "our_restart" and store.restart_taker in positions:
                attacker = store.restart_taker
                support = next((p.id for p in active if p.id not in (KEEPER_ID, attacker)), None)
                store.attacker = attacker
            if current == "our_restart" and store.restart_taker not in positions:
                store.restart_taker = attacker

            clearing = current == "normal" and keeper_can_clear(context.field, positions, ball, keeper_velocity)
            for player in active:
                if player.id == keeper:
                    if clearing:
                        player.action = "keeper:clear"
                        player.attack(shot_target(context.field, ball, store.restart_origin))
                    else:
                        player.action = "keeper:intercept" if keeper_intercept(context.field, ball, keeper_velocity) is not None else "keeper:track"
                        target, store.keeper_direction = keeper_tracking_target(context.field, positions[player.id], ball, store.keeper_direction, keeper_velocity)
                        store.keeper_target = target
                        player.walk_to(keeper_waypoint(positions[player.id], target), face=0.0)
                elif ball is None:
                    player.action = "ball:unknown"
                    player.stop()
                elif player.id == keeper or (player.id == attacker and not clearing):
                    player.action = "keeper:clear" if player.id == keeper else "roamer:attack"
                    restricted = store.restart_origin is not None and math.dist(ball, store.restart_origin) <= RESTART_SHOOT_DISTANCE_M
                    player.attack(shot_target(context.field, ball, store.restart_origin), power=RESTART_PASS_POWER if restricted else None)
                else:
                    player.action = "roamer:support"
                    if current == "our_restart" and store.restart_origin is not None and math.dist(ball, store.restart_origin) <= RESTART_SHOOT_DISTANCE_M:
                        target = support_target(context.field, store.restart_origin)
                    else:
                        target = support_target(context.field, ball)
                    if clearing and player.id == support:
                        target = target[0], -target[1]
                    player.move_to_position(target)

        store.phase = current
        keeper_trace(context, players, store, current)
        debugdraw.text(0, context.field.width / 2 + 0.2, f"phase={current} attacker={attacker}", ns="phase")
        for player in players:
            if player.pose is not None:
                debugdraw.text(player.pose.x, player.pose.y, f"{player.id}:{player.action}", ns=f"role_{player.id}")
