from game.core import GS, Hex, Terrain, TerrainProtectionRequest, Unit
from game.effects.modifiers import ForestStealthModifier
from game.effects.triggers import BurnOnCleanup, BurnOnWalkIn
from game.values import DamageType, Size


class Plains(Terrain): ...


class Forest(Terrain):
    """
    1 move in penalty.
    1 terrain protection for small and medium units.
    Small units have stealth.
    """

    blocks_vision = True

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 1

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        if request.unit.size.g() < Size.LARGE:
            return 1
            # if request.damage_signature.type in (DamageType.RANGED, DamageType.AOE):
            #     return 2
            # if request.damage_signature.type == DamageType.MELEE:
            #     return 1

        # if request.damage_signature.type in (DamageType.RANGED, DamageType.AOE):
        #     return 1
        return 0

    def create_effects(self, space: Hex) -> None:
        self.register_effects(ForestStealthModifier(space))


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
    1 move in penalty for units not moving in from high-ground.
    1 terrain protection against attacks from units not on high-ground.
    Blocks vision for units not on high-ground.
    """

    is_high_ground = True

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 0 if GS.map.hex_off(unit).terrain.is_high_ground else 1


class Water(Terrain):
    """Impassable."""

    is_water = True


class Magma(Terrain):
    """
    When a unit moves into this hex, and at the end of the round, apply 1 stack of <burn> to units on this hex.
    """

    def create_effects(self, space: Hex) -> None:
        # TODO should this also happen when units on this space are melee attacked? how should that be handled in general
        #  for these types of effects?
        self.register_effects(BurnOnWalkIn(space, 1), BurnOnCleanup(space, 1))


class Swamp(Terrain):
    """
    1 move out penalty.
    """

    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return 1
