import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import Terrain, Hex
from game.game.events import MoveUnit, Damage


class Plains(Terrain): ...


class Forest(Terrain): ...


class Hill(Terrain): ...


class Water(Terrain):

    def is_water(self) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class FireTerrainTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Damage(event.unit, self.amount))


class Magma(Terrain):

    def create_effects(self, space: Hex) -> None:
        self.register_effects(FireTerrainTrigger(space, 1))
