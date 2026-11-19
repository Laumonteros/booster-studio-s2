import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from team.src.field_player import Player as FieldPlayer
from team.src.player import Player as KeeperPlayer
from team.src.roster import PlayerRoster
from team.src.framework.types import ADULT_FIELD_DIMENSIONS as FIELD, Context, BallState
from team.src import field_params, param


class FieldV6Test(unittest.TestCase):
    def test_sample_player_and_utils_exact_except_isolated_imports(self):
        root=Path(__file__).parents[1]
        source=root/'sim-3v3-simple-framework/src'
        expected=(source/'player.py').read_text().replace('from .param import','from .field_params import').replace('from .utils.','from .field_utils.')
        self.assertEqual((root/'team/src/field_player.py').read_text(),expected)
        for p in (source/'utils').glob('*.py'):
            self.assertEqual((root/'team/src/field_utils'/p.name).read_text(),p.read_text().replace('from ..param import','from ..field_params import'))
        self.assertEqual((root/'team/src/field_params.py').read_text(),(source/'param.py').read_text().replace('SUPPORT_DIST_M = 3.0','SUPPORT_DIST_M = 2.0'))

    def test_roster_keeps_original_keeper_and_sample_field_players(self):
        self.assertIs(type(PlayerRoster(1,NS(team_id=1))),KeeperPlayer)
        self.assertIs(type(PlayerRoster(2,NS(team_id=1))),FieldPlayer)
        self.assertIs(type(PlayerRoster(3,NS(team_id=1))),FieldPlayer)
        self.assertEqual(field_params.KICK_ENTER_M,2.0)
        self.assertEqual(param.KICK_ENTER_M,1.5)

    def test_support_two_metres_goalward_in_both_halves(self):
        p=FieldPlayer(3,NS(team_id=1),None)
        for x,y in ((3,2),(-3,2)):
            p.context=Context(0,.03,1,FIELD,ball=BallState(x,y))
            with patch.object(p,'move_to_position') as move:
                p.support()
            tx,ty=move.call_args.args[0]
            self.assertAlmostEqual(((tx-x)**2+(ty-y)**2)**.5,2)
            self.assertLess(tx,x)
            self.assertLess(abs(ty),abs(y))

    def test_missing_ball_support_stops(self):
        p=FieldPlayer(3,NS(team_id=1),None)
        with patch.object(p,'stop') as stop:
            p.support()
        stop.assert_called_once()


if __name__=='__main__':unittest.main()
