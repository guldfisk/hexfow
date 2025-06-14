from abc import ABC, abstractmethod
from typing import Mapping, Any

from game.player import Player


class Connection(ABC):

    def __init__(self, player: Player):
        self.player = player

    @abstractmethod
    def send(self, values: Mapping[str, Any]) -> None: ...

    @abstractmethod
    def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]: ...
