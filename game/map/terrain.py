from game.core import Terrain, Hex, Unit, TerrainProtectionRequest
from game.effects.triggers import BurnOnWalkIn, BurnOnUpkeep
from game.values import Size, DamageType


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

# TODO block vision for small units? :^)
class Shrubs(Terrain):
    identifier = "shrubs"

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        if request.unit.size.g() == Size.SMALL:
            if request.damage_type == DamageType.RANGED:
                return 2
            return 1
        if (
            request.unit.size.g() == Size.MEDIUM
            and request.damage_type == DamageType.RANGED
        ):
            return 1

        return 0


class Hills(Terrain):
    identifier = "hills"

    def is_highground(self) -> bool:
        return True


class Water(Terrain):
    identifier = "water"

    def is_water(self) -> bool:
        return True


class Magma(Terrain):
    identifier = "magma"

    def create_effects(self, space: Hex) -> None:
        # TODO should this also happen when units on this space are melee attacked? how should that be handled in general
        #  for these types of effects?
        self.register_effects(BurnOnWalkIn(space, 1), BurnOnUpkeep(space, 1))
