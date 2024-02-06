import dataclasses

from game.game.objects import GameObject
from game.game.player import Player


@dataclasses.dataclass
class Status(GameObject):
    controller: Player = None


@dataclasses.dataclass
class Statusable(GameObject):
    statuses: list[Status] = dataclasses.field(default_factory=list)
