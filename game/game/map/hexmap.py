from __future__ import annotations

import dataclasses
import random
import typing as t
from enum import Enum

from game.game.objects import GameObject
from game.game.statuses import Statusable
from game.game.units import Unit


JSON = t.Mapping[str, t.Any]


class CubeCoordinate(t.NamedTuple):
    r: int
    h: int

    @property
    def l(self) -> int:
        return -sum(self)


class TerrainType(Enum):
    HILL = "hill"
    MOUNTAIN = "mountain"


@dataclasses.dataclass
class Hex(Statusable):
    position: CubeCoordinate = None
    terrain_type: TerrainType = None
    unit: Unit | None = None

    def serialize(self) -> JSON:
        return {
            "position": tuple(self.position),
            "terrain_type": self.terrain_type.value,
        }


@dataclasses.dataclass
class HexMap:
    hexes: t.Mapping[CubeCoordinate, Hex]

    def serialize(self) -> JSON:
        return {"hexes": [h.serialize() for h in self.hexes.values()]}



def generate_super_map(radius: int = 9) -> HexMap:
    hexes = [
        Hex(CubeCoordinate(r, h), terrain_type=random.choice(list(TerrainType)))
        for r in range(-radius, radius + 1)
        for h in range(-radius, radius + 1)
        if -radius <= -(r + h) <= radius
    ]
    return HexMap(hexes={h.position: h for h in hexes})
