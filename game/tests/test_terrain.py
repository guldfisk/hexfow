import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import Terrain, Hex, GS
from game.game.damage import DamageSignature
from game.game.events import MoveUnit, Damage, Upkeep


@dataclasses.dataclass(eq=False)
class DamageOnWalkIn(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Damage(event.unit, DamageSignature(self.amount)))


@dataclasses.dataclass(eq=False)
class DamageOnUpkeep(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: Upkeep) -> bool:
        return GS().map.unit_on(self.hex) is not None

    def resolve(self, event: Upkeep) -> None:
        if unit := GS().map.unit_on(self.hex):
            ES.resolve(Damage(unit, DamageSignature(self.amount)))


class InstantDamageMagma(Terrain):
    identifier = "instant_magma"

    def create_effects(self, space: Hex) -> None:
        self.register_effects(DamageOnWalkIn(space, 1), DamageOnUpkeep(space, 1))
