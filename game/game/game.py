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

from game.game.map.hexmap import CubeCoordinate


class Terrain:
    ...


class Landscape:
    terrain_map: Mapping[CubeCoordinate, Terrain]
    deployment_zones: Collection[AbstractSet[CubeCoordinate]]


class GameMap:
    def __init__(self, landscape: Landscape):
        self.landscape = landscape

    def get_units(self) -> Iterator[Unit]:
        ...

    def get_player_map_state(self, player: Player) -> PlayerGameState:
        ...


class PlayerMapState:
    ...


class Log:
    ...


class LegalAction:
    ...


class TakenAction:
    ...


class ActionSpace:
    options: Collection[LegalAction]


class PlayerGameState:
    map: PlayerMapState
    logs: Sequence[Log]
    action_space: ActionSpace | None


class AgentInterface:
    def __init__(self):
        self._history: list[PlayerGameState] = []

    def _send_to_remote(self, game_state: PlayerGameState) -> None:
        ...

    def send_game_state(self, game_state: PlayerGameState) -> None:
        if (
            not self._history
            or game_state.action_space
            or game_state != self._history[-1]
        ):
            self._history.append(game_state)
            self._send_to_remote(game_state)





# class MapType(ABC):
#
#     @abstractmethod
#     def generate_landscape(self) -> LandScape:
#         ...


class MapSpec(ABC):
    @abstractmethod
    def generate_landscape(self) -> Landscape:
        ...


# T = TypeVar('T')
#
# class GameSetting(ABC, Generic):
#     @abstractmethod
#     def validate


class Settings:
    map_spec: MapSpec
    army_strength: int



class Army:
    units: Collection[Unit]


class Game:
    def __init__(self, settings: Settings, armies: Collection[Army]):
        self.settings = settings
        self.is_finished = False
        self.turn_order = TurnOrder([Player() for _ in armies])
        self.map = GameMap(settings.map_spec.generate_landscape())

    def has_winner(self) -> bool:
        return len({unit.controller for unit in self.map.get_units()}) < 2

    def start(self):
        while not self.is_finished:
            if self.has_winner():
                self.is_finished = True
            self.turn_order.advance()


# class
