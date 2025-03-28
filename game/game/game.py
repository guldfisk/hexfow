from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    Sequence,
    Optional,
    Collection,
    Generic,
    TypeVar,
    Mapping,
    Iterator,
    AbstractSet,
)

from game.game.map.hexmap import CubeCoordinate, HexMap
from game.game.player import Player
from game.game.turn_order import TurnOrder


class Terrain:
    ...


# class Landscape:
#     terrain_map: Mapping[CubeCoordinate, Terrain]
    # TODO
    # deployment_zones: Collection[AbstractSet[CubeCoordinate]]



# class HexMap:
#     terrain_map: Mapping[CubeCoordinate, Terrain]

    # def __init__(self, landscape: Landscape):
    #     self.landscape = landscape

    # def get_units(self) -> Iterator[Unit]:
    #     ...



class Game:
    instance: Game | None = None

    def __init__(self, player_count: int):
        # self.settings = settings
        # self.is_finished = False
        self.turn_order = TurnOrder([Player() for _ in range(player_count)])
        # self.map = HexMap(settings.map_spec.generate_landscape())
        self.map = HexMap()

    # def has_winner(self) -> bool:
    #     return len({unit.controller for unit in self.map.get_units()}) < 2
    #
    # def start(self):
    #     while not self.is_finished:
    #         if self.has_winner():
    #             self.is_finished = True
    #         self.turn_order.advance()


# TODO
def GM() -> Game:
    return Game.instance
