import dataclasses

from game.game.objects import GameObject
from game.game.player import Player
from game.game.statuses import Statusable


@dataclasses.dataclass
class Unit(Statusable):
    controller: Player =  None
