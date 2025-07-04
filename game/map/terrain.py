from game.core import Terrain, Hex, Unit, TerrainProtectionRequest
from game.effects.triggers import BurnOnWalkIn, BurnOnCleanup
from game.values import Size, DamageType


class Plains(Terrain): ...


class Forest(Terrain):
    """
    1/2/2 melee/ranged/aoe protection for small/medium units.
    0/1/1 melee/ranged/aoe protection for large units.
    """

    blocks_vision = True

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


# TODO block vision for small units? :^)
class Shrubs(Terrain):
    """
    1/2/1 melee/ranged/aoe protection for small units.
    0/1/0 melee/ranged/aoe protection for medium units.
    """

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
    is_high_ground = True


class Water(Terrain):
    is_water = True


class Magma(Terrain):
    """
    When a unit moves into this hex, and at the end of the round, units on this hex suffers 1 <burn>.
    """

    def create_effects(self, space: Hex) -> None:
        # TODO should this also happen when units on this space are melee attacked? how should that be handled in general
        #  for these types of effects?
        self.register_effects(BurnOnWalkIn(space, 1), BurnOnCleanup(space, 1))
