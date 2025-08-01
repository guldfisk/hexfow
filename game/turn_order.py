from __future__ import annotations

from typing import Sequence

from game.player import Player


class TurnOrder:
    def __init__(self, players: Sequence[Player]):
        self.players = players
        self._active_player_index = 0

    @property
    def active_player(self) -> Player:
        return self.players[self._active_player_index]

    @property
    def all_players(self) -> list[Player]:
        return [
            self.players[(i + self._active_player_index) % len(self.players)]
            for i in range(len(self.players))
        ]

    def advance(self) -> Player:
        self._active_player_index = (self._active_player_index + 1) % len(self.players)
        return self.active_player

    def set_player_order(self, players: Sequence[Player]) -> None:
        self.players = players
        self._active_player_index = 0
