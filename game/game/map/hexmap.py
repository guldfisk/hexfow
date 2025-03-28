from __future__ import annotations

import dataclasses
import random
from enum import Enum
from typing import Mapping, Any, NamedTuple

from bidict import bidict

from game.game.has_effects import HasEffects
from game.game.statuses import HasStatuses
from game.game.units.unit import Unit


# from game.game.units import Unit


JSON = Mapping[str, Any]


class CubeCoordinate(NamedTuple):
    r: int
    h: int

    @property
    def l(self) -> int:
        return -sum(self)


class TerrainType(Enum):
    HILL = "hill"
    MOUNTAIN = "mountain"


@dataclasses.dataclass
class Hex(HasStatuses):
    position: CubeCoordinate
    terrain_type: TerrainType
    # unit: Unit | None = None

    # def serialize(self) -> JSON:
    #     return {
    #         "position": tuple(self.position),
    #         "terrain_type": self.terrain_type.value,
    #     }

class MovementException(Exception):
    ...

# @dataclasses.dataclass
class HexMap:

    def __init__(self, hexes: dict[CubeCoordinate, Hex]):
        self.hexes = hexes
        self.unit_positions: bidict[Unit, Hex] = bidict()

    def move_unit_to(self, unit: Unit, space: Hex) -> None:
        if self.unit_positions.inverse.get(space) is not None:
            raise MovementException()
        self.unit_positions[unit] = space

    def unit_on(self, space: Hex) -> Unit | None:
        return self.unit_positions.inverse.get(space)

    def position_of(self, unit: Unit) -> Hex:
        return self.unit_positions[unit]

    # def serialize(self) -> JSON:
    #     return {"hexes": [h.serialize() for h in self.hexes.values()]}



# def generate_super_map(radius: int = 9) -> HexMap:
#     hexes = [
#         Hex(CubeCoordinate(r, h), terrain_type=random.choice(list(TerrainType)))
#         for r in range(-radius, radius + 1)
#         for h in range(-radius, radius + 1)
#         if -radius <= -(r + h) <= radius
#     ]
#     return HexMap(hexes={h.position: h for h in hexes})
