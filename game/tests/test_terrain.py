import dataclasses
from typing import ClassVar

from events.eventsystem import ES, TriggerEffect
from game.core import GS, DamageSignature, Hex, Terrain
from game.events import Damage, MoveUnit, RoundCleanup


@dataclasses.dataclass(eq=False)
class DamageOnWalkIn(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Damage(event.unit, DamageSignature(self.amount, None)))


@dataclasses.dataclass(eq=False)
class DamageOnUpkeep(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.hex):
            ES.resolve(Damage(unit, DamageSignature(self.amount, None)))


class InstantDamageMagma(Terrain):
    identifier = "instant_magma"

    def create_effects(self, space: Hex) -> None:
        self.register_effects(DamageOnWalkIn(space, 1), DamageOnUpkeep(space, 1))
