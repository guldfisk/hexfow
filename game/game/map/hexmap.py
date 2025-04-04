from __future__ import annotations

import dataclasses
import random
from enum import Enum
from typing import Mapping, Any, NamedTuple

from bidict import bidict

from game.game.has_effects import HasEffects
from game.game.map.coordinates import CubeCoordinate
from game.game.map.landscape import Landscape
from game.game.map.terrain import TerrainType
from game.game.statuses import HasStatuses
from game.game.units.unit import Unit


@dataclasses.dataclass
class Hex(HasStatuses):
    position: CubeCoordinate
    terrain_type: TerrainType
    map: HexMap


class MovementException(Exception):
    ...


# @dataclasses.dataclass
class HexMap:
    def __init__(self, landscape: Landscape):
        self.hexes = {
            position: Hex(position=position, terrain_type=terrain_type, map=self)
            for position, terrain_type in landscape.terrain_map.items()
        }
        self.unit_positions: bidict[Unit, Hex] = bidict()

    def move_unit_to(self, unit: Unit, space: Hex) -> None:
        if self.unit_positions.inverse.get(space) is not None:
            raise MovementException()
        self.unit_positions[unit] = space

    def unit_on(self, space: Hex) -> Unit | None:
        return self.unit_positions.inverse.get(space)

    def position_of(self, unit: Unit) -> Hex:
        return self.unit_positions[unit]


# def generate_super_map(radius: int = 9) -> HexMap:
#     hexes = [
#         Hex(CubeCoordinate(r, h), terrain_type=random.choice(list(TerrainType)))
#         for r in range(-radius, radius + 1)
#         for h in range(-radius, radius + 1)
#         if -radius <= -(r + h) <= radius
#     ]
#     return HexMap(hexes={h.position: h for h in hexes})
