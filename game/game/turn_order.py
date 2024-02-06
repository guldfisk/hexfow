from __future__ import annotations

from typing import (
    Sequence,
)

from game.game.player import Player


class TurnOrder:
    def __init__(self, players: Sequence[Player]):
        self._players = players
        self._active_player_index = 0

    @property
    def active_player(self) -> Player:
        return self._players[self._active_player_index]

    def advance(self) -> Player:
        self._active_player_index = (self._active_player_index + 1) % len(self._players)
        return self.active_player

