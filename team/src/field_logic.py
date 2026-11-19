"""Official sample field logic, with its guard reserved for our existing keeper."""
import math
from enum import Enum

from .framework.types import KICKING_TEAM_NONE, Context, GameState, SetPlay
from .field_params import *
from .field_player import Player
from .field_utils import angle_to, clamp_inside_field, dist, opponent_goal, own_goal
from . import field_safety

class Phase(Enum):
    """Top-level match phase controlling normal play, restarts, and stops."""
    NORMAL = "normal"              # Normal contest while PLAYING
    OUR_KICKOFF = "our_kickoff"    # Our kickoff during early SET/PLAYING
    OPP_KICKOFF = "opp_kickoff"    # Opponent kickoff; keep clear
    OUR_SET_PLAY = "our_set_play"  # Our free kick, corner, or goal kick
    OPP_SET_PLAY = "opp_set_play"  # Opponent set play; keep clear
    READY = "ready"                # Move into READY positions
    STOPPED = "stopped"

def get_phase(context: Context) -> Phase:
    """Determine the current phase from the GameController state."""
    g = context.game
    if g is None:
        return Phase.STOPPED

    state = g.state

    # READY: move to ready positions.
    if state == GameState.READY:
        return Phase.READY

    # PLAYING: normal play or an active kickoff/set play.
    if state == GameState.PLAYING and not g.stopped:
        # For a set play, kicking_team identifies the team taking it.
        if g.set_play != SetPlay.NONE and g.kicking_team != KICKING_TEAM_NONE:
            our_team = context.team_id
            if g.kicking_team == our_team:
                return Phase.OUR_SET_PLAY
            else:
                return Phase.OPP_SET_PLAY

        # During the kickoff countdown, kicking_team identifies the taker.
        if g.secondary_time > 0 and g.kicking_team != KICKING_TEAM_NONE:
            our_team = context.team_id
            if g.kicking_team == our_team:
                return Phase.OUR_KICKOFF
            else:
                return Phase.OPP_KICKOFF

        # Normal play.
        return Phase.NORMAL

    # Remain stationary during SET, INITIAL, FINISHED, or a stoppage.
    return Phase.STOPPED

def get_set_play_type(context: Context) -> SetPlay:
    """Return the active set-play type, or ``SetPlay.NONE`` when unavailable.

    This reads the GameController's ``set_play`` field without identifying the
    taking team. :func:`get_phase` distinguishes OUR_SET_PLAY from OPP_SET_PLAY;
    this function only identifies the type.

    The seven possible values from framework.types.SetPlay are:
    - ``NONE``: no set play, such as normal play or a kickoff
    - ``DIRECT_FREE_KICK``: a direct free kick that may score immediately
    - ``INDIRECT_FREE_KICK``: another player must touch the ball before a goal
    - ``PENALTY_KICK``: a penalty kick
    - ``THROW_IN``: a kick-in from touch
    - ``GOAL_KICK``: a goal kick
    - ``CORNER_KICK``: a corner kick
    """
    g = context.game
    if g is None:
        return SetPlay.NONE
    return g.set_play

def _clear_normal_sticky(store) -> None:
    store.normal_attacker = None

def _player_dist_to_position(p: Player, target: tuple[float, float]) -> float:
    """Return infinity when the player's position is unknown."""
    pose = p.pose
    if pose is None:
        return math.inf
    return dist(pose.x, pose.y, *target)

def _player_dist_to_ball(context: Context, p: Player) -> float:
    """Return a player's distance to the ball's current position."""
    ball = context.ball
    return (
        _player_dist_to_position(p, (ball.x, ball.y)) + _fallen_time_cost(p)
        if ball is not None else math.inf
    )

def _fallen_time_cost(p: Player) -> float:
    return FALLEN_COST if p.is_fallen else 0.0

def _select_closest_attacker(
    context: Context,
    players: list[Player],
    preferred_id: int | None = None,
) -> Player:
    """Select the player with the lowest effective distance to the ball.

    ``players`` must be nonempty, ready, and have known poses. Normal play and
    kickoffs share this selection logic.
    """
    ranked = [(p, _player_dist_to_ball(context, p)) for p in players]
    best, best_dist = min(ranked, key=lambda item: item[1])
    preferred = next((item for item in ranked if item[0].id == preferred_id), None)
    if (
        preferred is not None
        and preferred[1] <= best_dist + ATTACKER_KEEP_DIST_MARGIN_M
    ):
        return preferred[0]
    return best

def _act_normal(context: Context, players: list[Player], store) -> None:
    """Assign the nearest field player to attack and the other to support.

    ``players`` contains ready players with known poses. Assign and execute
    their roles directly here.
    """
    if not players:
        return

    attacker = _select_closest_attacker(
        context, players, getattr(store, "normal_attacker", None),
    )
    store.normal_attacker = attacker.id
    attacker.action = "attack"
    attacker.attack()

    rest = [p for p in players if p is not attacker]

    # All other players support.
    for p in rest:
        p.action = "support"
        field_safety.support(context, p, store)

def _act_our_kickoff(context: Context, players: list[Player], store) -> None:
    """Lock the nearest kickoff taker, assign a guard, and leave others in support."""
    if not players:
        return

    active_ids = {p.id for p in players}
    if store.prev_phase != Phase.OUR_KICKOFF or store.kickoff_taker not in active_ids:
        # Select a new taker when entering the kickoff phase.
        store.kickoff_taker = _select_closest_attacker(context, players).id

    attacker_id = store.kickoff_taker
    attacker = next((p for p in players if p.id == attacker_id), None)
    if attacker is None:
        return

    attacker.action = "kickoff"
    attacker.kick(0.1, KICK_POWER_OUR_KICKOFF)

    rest = [p for p in players if p is not attacker]

    for p in rest:
        p.action = "stay"
        p.stop()

def _act_opp_kickoff(context: Context, players: list[Player]) -> None:
    """Guard with one player while the others wait outside the center circle."""
    if not players:
        return
    rest = players
    r = context.field.circle_radius
    slots = [(-r - 0.5, 0.0), (-r - 2.0, 0.5)]
    for p, target in zip(rest, slots):
        p.action = "opp_kickoff:ready"
        p.walk_to(target, avoid_ball=True, avoid_robots=True)

def _act_our_set_play(context: Context, players: list[Player], store) -> None:
    """Dispatch our set play by type. TODO: add strategy; defaults to normal."""
    set_play = get_set_play_type(context)
    if set_play == SetPlay.THROW_IN:
        _act_normal(context, players, store)
        return
    if set_play == SetPlay.CORNER_KICK:
        _act_normal(context, players, store)
        return
    if set_play == SetPlay.GOAL_KICK:
        _act_normal(context, players, store)
        return
    _act_normal(context, players, store)

def _act_opp_set_play(context: Context, players: list[Player], store) -> None:
    """Retreat directly from the ball; wait until the official phase changes."""
    ball = context.ball
    # Account for walk_to's arrival tolerance when targeting the 1.5 m boundary.
    radius = OPP_SET_PLAY_CLEARANCE_M + ARRIVE_DIST
    half_l = context.field.length / 2.0 - OPP_SET_PLAY_FIELD_MARGIN_M
    half_w = context.field.width / 2.0 - OPP_SET_PLAY_FIELD_MARGIN_M
    for p in players:
        pose = p.pose
        p.action = "opp_set:wait"
        if ball is None or pose is None:
            p.stop()
            continue
        if dist(pose.x, pose.y, ball.x, ball.y) >= OPP_SET_PLAY_CLEARANCE_M:
            p.stop()
            continue

        # The radial exit is shortest. At the field edge, also consider the
        # retreat circle's intersections with the in-field boundary.
        outward = angle_to(ball.x, ball.y, pose.x, pose.y)
        candidates = [(
            ball.x + math.cos(outward) * radius,
            ball.y + math.sin(outward) * radius,
        )]
        for x in (-half_l, half_l):
            remaining = radius ** 2 - (x - ball.x) ** 2
            if remaining >= 0.0:
                offset = math.sqrt(remaining)
                candidates.extend((x, ball.y + sign * offset) for sign in (-1.0, 1.0))
        for y in (-half_w, half_w):
            remaining = radius ** 2 - (y - ball.y) ** 2
            if remaining >= 0.0:
                offset = math.sqrt(remaining)
                candidates.extend((ball.x + sign * offset, y) for sign in (-1.0, 1.0))
        candidates = [
            t for t in candidates
            if t == clamp_inside_field(context, *t, margin=OPP_SET_PLAY_FIELD_MARGIN_M)
        ]
        if not candidates:
            p.stop()
            continue

        px, py = pose.x, pose.y
        target = min(candidates, key=lambda t: dist(px, py, *t))
        # Short omnidirectional steps follow the retreat line directly.
        # Do not invoke path avoidance: the movement is away from the ball.
        length = dist(pose.x, pose.y, *target)
        ratio = min(1.0, OMNI_DIST / (2.0 * length))
        step = (
            pose.x + (target[0] - pose.x) * ratio,
            pose.y + (target[1] - pose.y) * ratio,
        )
        p.action = "opp_set:retreat"
        p.walk_to(step, face=angle_to(pose.x, pose.y, ball.x, ball.y))

def _act_ready(context: Context, players: list[Player]) -> None:
    """Move each player to a ready position."""
    game = context.game
    our_kickoff = game is not None and game.kicking_team == context.team_id
    field = context.field
    # Our kickoff priority: center-circle edge, goal-area center, then left side.
    if our_kickoff:
        if len(players) >= 1:
            p1 = players[0]
            p1.action = "ready"
            p1.walk_to(
                (-field.circle_radius, 0.0),
                face=0.0,
                avoid_ball=True,
                avoid_robots=True,
            )
        if len(players) >= 2:
            p2 = players[1]
            p2.action = "ready"
            p2.walk_to(
                (-0.5, field.circle_radius + 2),
                face=0.0,
                avoid_ball=True,
                avoid_robots=True,
            )
        if len(players) >= 3:
            p3 = players[2]
            p3.action = "ready"
            p3.walk_to(
                (-0.5, field.circle_radius + 2),
                face=0.0,
                avoid_ball=True,
                avoid_robots=True,
            )
    # Opponent kickoff priority: outside center circle, goal area, then penalty area.
    else:
        if len(players) >= 1:
            p1 = players[0]
            p1.action = "ready"
            p1.walk_to(
                (-field.circle_radius - 0.5, 0.0),
                face=0.0,
                avoid_ball=True,
                avoid_robots=True,
            )
        if len(players) >= 2:
            p2 = players[1]
            p2.action = "ready"
            p2.walk_to(
                (-field.length / 2.0 + field.penalty_area_length, 0.0),
                face=0.0,
                avoid_ball=True,
                avoid_robots=True,
            )
        if len(players) >= 3:
            p3 = players[2]
            p3.action = "ready"
            p3.walk_to(
                (-field.length / 2.0 + field.penalty_area_length, 0.0),
                face=0.0,
                avoid_ball=True,
                avoid_robots=True,
            )


def run(context, players, store):
    current = get_phase(context)
    store.prev_phase, store.cur_phase = store.cur_phase, current
    if current != Phase.NORMAL:
        _clear_normal_sticky(store)
    handled = field_safety.restart(context, players, store, current.value)
    if current in (Phase.OPP_KICKOFF, Phase.OPP_SET_PLAY):
        field_safety.clear_opponent(context, players)
    elif handled:
        pass
    elif current == Phase.NORMAL:
        _act_normal(context, players, store)
    elif current == Phase.OUR_KICKOFF:
        _act_our_kickoff(context, players, store)
    elif current == Phase.OPP_KICKOFF:
        _act_opp_kickoff(context, players)
    elif current == Phase.OUR_SET_PLAY:
        _act_our_set_play(context, players, store)
    elif current == Phase.OPP_SET_PLAY:
        _act_opp_set_play(context, players, store)
    elif current == Phase.READY:
        _act_ready(context, players)
    else:
        for p in players:
            p.action = 'stopped'
            p.stop()
    return store.kickoff_taker if current == Phase.OUR_KICKOFF else store.normal_attacker
