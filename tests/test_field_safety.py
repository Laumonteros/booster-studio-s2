import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS

from team.src import field_safety as safety
from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD, BallState, Context, GameControlState, GameState, Pose2D, SetPlay
from test_team_dispatch import FakePlayer


class FieldSafetyTest(unittest.TestCase):
    def setUp(self):
        self.store=NS()
        self.ctx=Context(0,.03,1,FIELD,ball=BallState(),game=GameControlState(state=GameState.PLAYING,kicking_team=1,set_play=SetPlay.THROW_IN))
        self.players=[FakePlayer(2,(-.5,0,0)),FakePlayer(3,(0,-1.8,0))]
        self.bind()

    def bind(self):
        for p in self.players:p.context=self.ctx

    def restart(self,phase='our_set_play'):
        self.bind()
        return safety.restart(self.ctx,self.players,self.store,phase)

    def test_initial_pass_is_short_lateral_and_different_receiver(self):
        self.assertTrue(self.restart())
        self.assertEqual(self.players[0].calls[-1],('kick',-math.pi/2,1.5))
        self.assertEqual(self.store.restart_pass['receiver'],3)

    def test_latch_survives_ball_free_and_expiration_without_displacement(self):
        self.restart()
        self.ctx=replace(self.ctx,now=100,game=GameControlState(state=GameState.PLAYING))
        self.restart('normal')
        self.assertEqual(self.players[0].calls[-1][0],'kick')
        self.assertEqual(self.players[0].calls[-1][-1],1.5)
        self.assertEqual(self.store.restart_pass['taker'],2)

    def test_receiver_only_shoots_away_from_origin(self):
        self.restart()
        self.ctx=replace(self.ctx,ball=BallState(0,-.8),game=GameControlState(state=GameState.PLAYING))
        self.restart('normal')
        self.assertEqual(self.players[1].calls[-1][-1],1.5)
        self.ctx=replace(self.ctx,ball=BallState(0,-1.2))
        self.restart('normal')
        self.assertEqual(self.players[1].calls[-1][0],'attack')
        self.assertNotEqual(self.players[0].calls[-1][0],'attack')

    def test_new_restart_replaces_old_origin(self):
        self.restart()
        self.ctx=replace(self.ctx,game=replace(self.ctx.game,stopped=True),ball=BallState(3,4))
        self.restart('stopped')
        self.ctx=replace(self.ctx,game=replace(self.ctx.game,stopped=False))
        self.restart()
        self.assertEqual(self.store.restart_pass['origin'],(3,4))

    def test_missing_partner_or_ball_does_not_shoot(self):
        self.players=self.players[:1]
        self.assertTrue(self.restart())
        self.assertNotEqual(self.players[0].calls[-1][0],'attack')
        self.ctx=replace(self.ctx,ball=None)
        self.restart('normal')
        self.assertEqual(self.players[0].calls[-1],('stop',))

    def test_empty_missing_game_and_stopped(self):
        self.players=[]
        self.ctx=replace(self.ctx,game=None)
        self.assertFalse(self.restart('stopped'))
        safety.clear_opponent(self.ctx,[])

    def test_exit_is_radial_with_fixed_heading_and_margin(self):
        self.players[0].pose=Pose2D(.5,.5,math.pi/2)
        safety.clear_opponent(self.ctx,self.players[:1])
        vx,vy,w=self.players[0].calls[-1][1]
        self.assertGreater(-vy,0)
        self.assertAlmostEqual(vx,-vy)
        self.assertEqual(w,0)
        self.assertLessEqual(math.hypot(vx,vy),.65+1e-8)
        t=safety.radial_target(self.ctx,(.5,.5),(0,0),2.2)
        self.assertGreaterEqual(math.dist(t,(0,0)),1.95)

    def test_field_edge_exit_stays_inside_and_outside_radius(self):
        for ball,pose in (((6,2),(6.7,2)),((3,4.45),(3,4.2)),((-6,-2),(-6.7,-2))):
            t=safety.radial_target(self.ctx,pose,ball,2.2)
            self.assertLessEqual(abs(t[0]),6.75+1e-8)
            self.assertLessEqual(abs(t[1]),4.25+1e-8)
            self.assertAlmostEqual(math.dist(t,ball),2.2)

    def test_clear_or_missing_ball_waits(self):
        self.players[0].pose=Pose2D(-3,0,0)
        safety.clear_opponent(self.ctx,self.players[:1])
        self.assertEqual(self.players[0].calls[-1],('stop',))
        safety.clear_opponent(replace(self.ctx,ball=None),self.players[:1])
        self.assertEqual(self.players[0].calls[-1],('stop',))

    def test_inactive_support_escapes_slowly_and_does_not_oscillate(self):
        p=self.players[0];p.pose=Pose2D(-2,0,0)
        safety.support(self.ctx,p,self.store)
        safety.support(replace(self.ctx,now=3.1),p,self.store)
        self.assertEqual(p.calls[-1],('velocity',(-.35,0.,0.)))
        p.pose=Pose2D(-2.3,0,0)
        safety.support(replace(self.ctx,now=4.1),p,self.store)
        self.assertEqual(p.calls[-1][0],'velocity')
        p.pose=Pose2D(-3.6,0,0)
        safety.support(replace(self.ctx,now=8),p,self.store)
        self.assertEqual(p.calls[-1],('stop',))

    def test_support_missing_ball_stops(self):
        safety.support(replace(self.ctx,ball=None),self.players[0],self.store)
        self.assertEqual(self.players[0].calls[-1],('stop',))


if __name__=='__main__':unittest.main()
