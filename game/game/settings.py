from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    Collection,
    Mapping,
    AbstractSet,
)

from game.game.creatures.creature import Creature
from game.game.map.hexmap import CubeCoordinate
from game.game.terrain.terrain import Terrain


class Landscape:
    terrain_map: Mapping[CubeCoordinate, type[Terrain]]
    deployment_zones: Collection[AbstractSet[CubeCoordinate]]


class MapSpec(ABC):
    @abstractmethod
    def generate_landscape(self) -> Landscape:
        ...


class Settings:
    map_spec: MapSpec
    reserve_strength: int
    army_strength: int


class Reserve:
    units: Collection[Creature]


class Army:
    units: Collection[Creature]
