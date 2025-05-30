import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import Terrain, Hex, GS, Unit, TerrainProtectionRequest
from game.game.damage import DamageSignature
from game.game.events import MoveUnit, Damage, Upkeep
from game.game.values import Size, DamageType


class Plains(Terrain): ...


class Forest(Terrain):

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 1

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        if request.unit.size.g() < Size.LARGE:
            if request.damage_type == DamageType.RANGED:
                return 2
            if request.damage_type == DamageType.MELEE:
                return 1

        if request.damage_type == DamageType.RANGED:
            return 1

    def blocks_vision(self) -> bool:
        return True


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


class Magma(Terrain):

    def create_effects(self, space: Hex) -> None:
        self.register_effects(DamageOnWalkIn(space, 1), DamageOnUpkeep(space, 1))
