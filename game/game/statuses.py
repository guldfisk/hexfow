import dataclasses
from enum import StrEnum, auto

from game.game.has_effects import HasEffects
from game.game.player import Player


class StatusType(StrEnum):
    BUFF = auto()
    DEBUFF = auto()
    NEUTRAL = auto()

@dataclasses.dataclass
class Status(HasEffects):
    # controller: Player = None
    type_: StatusType


@dataclasses.dataclass
class HasStatuses(HasEffects):
    statuses: list[Status] = dataclasses.field(default_factory=list, init=False)
    # statuses: list[Status]
