from game.core import Terrain, Hex, Unit, TerrainProtectionRequest
from game.effects.triggers import BurnOnWalkIn, BurnOnCleanup
from game.values import Size, DamageType


class Plains(Terrain): ...


class Forest(Terrain):
    """
    1/2/2 melee/ranged/aoe protection for small/medium units.
    0/1/1 melee/ranged/aoe protection for large units.
    1 move in penalty.
    """

    blocks_vision = True

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 1

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        if request.unit.size.g() < Size.LARGE:
            if request.damage_signature.type in (DamageType.RANGED, DamageType.AOE):
                return 2
            if request.damage_signature.type == DamageType.MELEE:
                return 1

        if request.damage_signature.type in (DamageType.RANGED, DamageType.AOE):
            return 1
        return 0


# TODO block vision for small units? :^)
class Shrubs(Terrain):
    """
    0/1/1 melee/ranged/aoe protection for small units.
    """

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        if request.unit.size.g() == Size.SMALL:
            if request.damage_signature.type == DamageType.MELEE:
                return 0
            return 1

        return 0


class Hills(Terrain):
    """
    +1 move in cost for units moving in from non high-ground spaces (can still move in with 1 movement point if it's the first action).
    +1 terrain protection against attacks from units not on high-ground.
    Blocks vision for units not on high-ground.
    """

    is_high_ground = True


class Water(Terrain):
    """Impassable."""

    is_water = True


class Magma(Terrain):
    """
    When a unit moves into this hex, and at the end of the round, units on this hex suffers 1 <burn>.
    """

    def create_effects(self, space: Hex) -> None:
        # TODO should this also happen when units on this space are melee attacked? how should that be handled in general
        #  for these types of effects?
        self.register_effects(BurnOnWalkIn(space, 1), BurnOnCleanup(space, 1))
