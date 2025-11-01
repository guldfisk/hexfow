from game.core import GS, Hex, Terrain, TerrainProtectionRequest, Unit
from game.effects.modifiers import ForestStealthModifier
from game.effects.triggers import BurnOnCleanup, BurnOnWalkIn
from game.values import Size


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
        return 1 if request.unit.size.g() < Size.LARGE else 0

    def create_effects(self, space: Hex) -> None:
        self.register_effects(ForestStealthModifier(space))


class Hills(Terrain):
    """
    1 move in penalty for units not moving in from high-ground.
    1 terrain protection against attacks from units not on high-ground.
    Blocks vision for units not on high-ground.
    Units on high ground can see over other units and terrain not on high ground.
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
        self.register_effects(BurnOnWalkIn(space, 1), BurnOnCleanup(space, 1))


class Swamp(Terrain):
    """
    1 move out penalty.
    """

    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return 1
