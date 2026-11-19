import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock

from team.src import field_logic, rebound_support as rebound
from team.src.field_player import Player
from team.src.framework.types import (
    ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context, GameControlState,
    GameState, Pose2D, SetPlay,
)


class ReboundSupportTest(unittest.TestCase):
    def setUp(self):
        self.attacker=NS(id=2,pose=Pose2D(2.5,0,0))
        self.player=NS(id=3,pose=Pose2D(1.,2.,0),move_to_position=Mock(),walk_to=Mock())
        self.ctx=Context(0.,.033,1,FIELD,game=GameControlState(state=GameState.PLAYING),
                         ball=BallState(3.,0.))

    def test_goalward_flank_and_defensive_trailing_position(self):
        point=rebound.target(self.ctx,self.player,self.attacker)
        self.assertGreater(point[0],self.ctx.ball.x)
        self.assertAlmostEqual(abs(point[1]),1.25)
        defensive=replace(self.ctx,ball=BallState(-3.,0.))
        point=rebound.target(defensive,self.player,self.attacker)
        self.assertLess(point[0],-3.)
        self.assertLess(math.dist(point,(-3,0)),2.)

    def test_selected_shot_lane_and_attacker_spacing(self):
        self.attacker._normal_shot_y=1.
        self.ctx=replace(self.ctx,ball=BallState(4.,0.))
        self.player.pose=Pose2D(3,2,0)
        point=rebound.target(self.ctx,self.player,self.attacker)
        dx,dy=3.,1.
        self.assertGreaterEqual(abs((point[0]-4)*dy-point[1]*dx)/math.hypot(dx,dy),.8)
        self.assertGreaterEqual(math.dist(point,rebound.position(self.attacker)),.9)

    def test_touchlines_and_endlines_stay_inside_margin(self):
        for x in(-6.8,0.,6.8):
            for y in(-4.3,0.,4.3):
                ctx=replace(self.ctx,ball=BallState(x,y))
                point=rebound.target(ctx,self.player,self.attacker)
                self.assertLessEqual(abs(point[0]),6.25)
                self.assertLessEqual(abs(point[1]),3.75)
                dx,dy=7.25-x,-y
                projection=((point[0]-x)*dx+(point[1]-y)*dy)/(dx*dx+dy*dy)
                if 0<projection<1:
                    self.assertGreaterEqual(abs((point[0]-x)*dy-(point[1]-y)*dx)/math.hypot(dx,dy),.8)

    def test_side_hysteresis_does_not_follow_small_pose_noise(self):
        first=rebound.target(self.ctx,self.player,self.attacker)
        self.player.pose=Pose2D(1.,-.01,0)
        self.assertEqual(rebound.target(self.ctx,self.player,self.attacker),first)

    def test_nearby_patrol_has_short_steps_and_no_commanded_yaw(self):
        self.player.pose=Pose2D(4.5,1.25,.7)
        self.assertTrue(rebound.handle(self.ctx,self.player,self.attacker))
        initial=self.player.walk_to.call_args.args[0]
        for i in range(1,61):
            rebound.handle(replace(self.ctx,now=i/30),self.player,self.attacker)
        args,kwargs=self.player.walk_to.call_args
        self.assertNotEqual(args[0],initial)
        self.assertLessEqual(math.dist(args[0],rebound.position(self.player)),.35+1e-9)
        self.assertEqual(kwargs['face'],self.player.pose.theta)
        self.assertTrue(kwargs['avoid_ball']and kwargs['avoid_robots'])
        self.assertEqual(kwargs['arrive_dist'],.04)

    def test_stalled_pose_escapes_even_when_commands_were_active(self):
        for i in range(101):
            rebound.handle(replace(self.ctx,now=i/30),self.player,self.attacker)
        self.assertEqual(self.player.action,'support:escape')
        point=self.player.move_to_position.call_args.args[0]
        self.assertGreaterEqual(math.dist(point,(3.,0.)),3.3)
        self.player.pose=Pose2D(point[0],point[1],0)
        rebound.handle(replace(self.ctx,now=3.4),self.player,self.attacker)
        self.assertEqual(self.player.action,'support:rebound')

    def test_physical_progress_and_observation_gaps_reset_stall_budget(self):
        for i in range(151):
            self.player.pose=Pose2D(1.+i*.01,2.,0)
            rebound.handle(replace(self.ctx,now=i/30),self.player,self.attacker)
            self.assertNotEqual(self.player.action,'support:escape')
        rebound.handle(replace(self.ctx,now=50.),self.player,self.attacker)
        self.assertNotEqual(self.player.action,'support:escape')

    def test_keeper_missing_observations_and_all_restarts_are_bypassed(self):
        for ctx in (replace(self.ctx,ball=None),replace(self.ctx,game=None),
                    replace(self.ctx,game=replace(self.ctx.game,stopped=True))):
            self.assertFalse(rebound.handle(ctx,self.player,self.attacker))
        for state in GameState:
            if state!=GameState.PLAYING:
                self.assertFalse(rebound.handle(replace(self.ctx,game=replace(self.ctx.game,state=state)),self.player,self.attacker))
        for play in SetPlay:
            if play!=SetPlay.NONE:
                self.assertFalse(rebound.handle(replace(self.ctx,game=replace(self.ctx.game,set_play=play)),self.player,self.attacker))
        for team in(1,2):
            self.assertFalse(rebound.handle(replace(self.ctx,game=replace(self.ctx.game,kicking_team=team,secondary_time=10)),self.player,self.attacker))
        self.player.id=1
        self.assertFalse(rebound.handle(self.ctx,self.player,self.attacker))
        self.player.id=3;self.player.pose=None
        self.assertFalse(rebound.handle(self.ctx,self.player,self.attacker))
        self.player.move_to_position.assert_not_called()

    def test_real_player_native_task_is_released_before_support_moves(self):
        backend=Mock();player=Player(3,NS(team_id=1),backend)
        player.context=replace(self.ctx,teammates={3:NS(pose=Pose2D(4.5,1.25,0))})
        rebound.handle(player.context,player,self.attacker)
        backend.release_kick.assert_called()
        backend.kick.assert_not_called()
        vx,vy,yaw=backend.set_velocity.call_args.args
        self.assertLessEqual(math.hypot(vx,vy),.525+1e-9)
        self.assertEqual(yaw,0.)

    def test_normal_dispatch_only_and_missing_ball_stop(self):
        a=Mock(id=2,pose=Pose2D(2.8,0,0),is_fallen=False,_normal_shot_y=0.)
        p=Mock(id=3,pose=Pose2D(0,2,0),is_fallen=False)
        p._rebound_side=None;p._rebound_seen=None
        field_logic._act_normal(self.ctx,[a,p],NS(normal_attacker=None))
        self.assertEqual(p.action,'support:rebound')
        a.attack.assert_called_once();p.support.assert_not_called()
        missing=replace(self.ctx,ball=None)
        real=Player(3,NS(team_id=1),Mock());real.context=missing
        self.assertFalse(rebound.handle(missing,real,self.attacker))
        real.support();real._backend.kick.assert_not_called()


if __name__=='__main__':unittest.main()
