from .field_player import Player as FieldPlayer
from .player import Player as KeeperPlayer
from .telemetry import instrument_player


Keeper = instrument_player(KeeperPlayer)
Field = instrument_player(FieldPlayer)


class PlayerRoster:
    def __new__(cls, player_id, config, _backend=None):
        return (Keeper if player_id == 1 else Field)(player_id, config, _backend)
