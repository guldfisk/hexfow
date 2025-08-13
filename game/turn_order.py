from __future__ import annotations

from typing import Sequence, Iterator

from game.player import Player


class TurnOrder:
    def __init__(self, players: Sequence[Player]):
        self.original_order = players
        self._players = players
        self._active_player_index = 0

    @property
    def active_player(self) -> Player:
        return self._players[self._active_player_index]

    @property
    def all_players(self) -> list[Player]:
        return [
            self._players[(i + self._active_player_index) % len(self._players)]
            for i in range(len(self._players))
        ]

    def advance(self) -> Player:
        self._active_player_index = (self._active_player_index + 1) % len(self._players)
        return self.active_player

    def set_player_order(self, players: Sequence[Player]) -> None:
        self._players = players
        self._active_player_index = 0

    def __iter__(self) -> Iterator[Player]:
        yield from self.all_players