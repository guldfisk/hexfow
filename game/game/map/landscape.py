from typing import Mapping

from game.game.map.coordinates import CubeCoordinate
from game.game.terrain.terrain import Terrain


class Landscape:
    terrain_map: Mapping[CubeCoordinate, type[Terrain]]
    # deployment_zones: Collection[AbstractSet[CubeCoordinate]]