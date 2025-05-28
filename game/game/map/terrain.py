import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import Terrain, Hex, GS
from game.game.events import MoveUnit, Damage, Upkeep


class Plains(Terrain): ...


class Forest(Terrain): ...


class Hill(Terrain): ...


class Water(Terrain):

    def is_water(self) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class DamageOnWalkIn(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Damage(event.unit, self.amount))


@dataclasses.dataclass(eq=False)
class DamageOnUpkeep(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: Upkeep) -> bool:
        return GS().map.unit_on(self.hex) is not None

    def resolve(self, event: Upkeep) -> None:
        if unit := GS().map.unit_on(self.hex):
            ES.resolve(Damage(unit, self.amount))


class Magma(Terrain):

    def create_effects(self, space: Hex) -> None:
        self.register_effects(DamageOnWalkIn(space, 1), DamageOnUpkeep(space, 1))
