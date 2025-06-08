import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import Terrain, Hex, GS, Unit, TerrainProtectionRequest
from game.game.events import MoveUnit, Upkeep, ApplyStatus
from game.game.statuses import Burn
from game.game.values import Size, DamageType


class Plains(Terrain):
    identifier = "plains"


class Forest(Terrain):
    identifier = "forest"

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 1

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        if request.unit.size.g() < Size.LARGE:
            if request.damage_type in (DamageType.RANGED, DamageType.AOE):
                return 2
            if request.damage_type == DamageType.MELEE:
                return 1

        if request.damage_type in (DamageType.RANGED, DamageType.AOE):
            return 1
        return 0

    def blocks_vision(self) -> bool:
        return True


class Hills(Terrain):
    identifier = "hills"


class Water(Terrain):
    identifier = "water"

    def is_water(self) -> bool:
        return True


# TODO should be able to have triggers listening on multiple events, it should even
#  work with making the generic type a union.

@dataclasses.dataclass(eq=False)
class BurnOnWalkIn(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(ApplyStatus(unit=event.unit, status_type=Burn, by=None, stacks=1))


@dataclasses.dataclass(eq=False)
class BurnOnUpkeep(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: Upkeep) -> bool:
        return GS().map.unit_on(self.hex) is not None

    def resolve(self, event: Upkeep) -> None:
        if unit := GS().map.unit_on(self.hex):
            ES.resolve(ApplyStatus(unit=unit, status_type=Burn, by=None, stacks=1))


class Magma(Terrain):
    identifier = "magma"

    def create_effects(self, space: Hex) -> None:
        # TODO should this also happen when units on this space are melee attacked? how should that be handled in general
        #  for these types of effects?
        self.register_effects(BurnOnWalkIn(space, 1), BurnOnUpkeep(space, 1))
