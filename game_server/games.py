from __future__ import annotations

import json
import threading
import time
import traceback
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Mapping, Any, Callable
from uuid import UUID

from sqlalchemy import select, Exists

from events.eventsystem import ES, EventSystem
from events.exceptions import GameException
from game.core import GameState, GS
from game.events import SpawnUnit, Play
from game.interface import Connection
from game.player import Player
from game_server.scenarios import get_playtest_scenario
from model.engine import SS
from model.models import Seat, Game


class GameClosed(GameException):
    pass


class GameManager:
    def __init__(self):
        self._running: list[GameRunner] = []
        self._interface_map: dict[UUID, SeatInterface] = {}
        self._lock = threading.Lock()

    def register(self, game: GameRunner) -> None:
        with self._lock:
            self._running.append(game)
            for id_, interface in game.seat_map.items():
                self._interface_map[id_] = interface

    def deregister(self, game: GameRunner) -> None:
        with self._lock:
            self._running.remove(game)
            for id_ in game.seat_map.keys():
                del self._interface_map[id_]

    def stop_all(self) -> None:
        with self._lock:
            for game in self._running:
                game.stop()

    def get_seat_interface(self, seat_id: UUID) -> SeatInterface:
        with self._lock:
            if seat_id in self._interface_map:
                return self._interface_map[seat_id]

            game = SS.scalar(
                select(Game).where(
                    Exists(
                        select(Seat.id).where(
                            Seat.game_id == Game.id, Seat.id == seat_id
                        )
                    )
                )
            )

            # TODO
            if game:
                runner = GameRunner(game)
                runner.start()
                # TODO ultra tikes
                for i in range(10):
                    if not runner.seat_map:
                        time.sleep(0.1)
                return runner.seat_map[seat_id]


GM = GameManager()


class SeatInterface(Connection):
    def __init__(self, player: Player, game: GameRunner):
        super().__init__(player)
        self.game_runner = game
        self._latest_frame = None
        self._lock = threading.Lock()
        self.in_queue = SimpleQueue()
        self._callbacks: list[Callable[[str], ...]] = []

    def register_callback(self, f: Callable[[str], ...]) -> None:
        with self._lock:
            self._callbacks.append(f)
            if self._latest_frame is not None:
                f(json.dumps(self._latest_frame))

    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._callbacks)

    def deregister_callback(self, f: Callable[[str], ...]) -> None:
        with self._lock:
            self._callbacks.remove(f)

    def _send_frame(self, values: Mapping[str, Any]) -> None:
        with self._lock:
            self._latest_frame = values
            for f in self._callbacks:
                f(json.dumps(values))

    def send(self, values: Mapping[str, Any]) -> None:
        self._send_frame(values)

    def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
        self._send_frame(values)
        while self.game_runner.is_running:
            try:
                response = self.in_queue.get(timeout=1)
                return response
            except Empty:
                pass
        raise GameClosed()


class Cleaner(Thread):

    def __init__(self, game_runner: GameRunner, delay: int):
        super().__init__()
        self._runner = game_runner
        self._delay = delay
        self._is_running = False

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        for i in range(self._delay):
            if not self._is_running:
                return
            time.sleep(1)
        self._runner.stop_if_deserted()


class GameRunner(Thread):
    def __init__(self, game: Game):
        super().__init__()
        self._scenario = get_playtest_scenario()
        self._game = game
        self._lock = threading.Lock()
        self._is_running = False
        self._children: list[Thread] = []

        self.seat_map: dict[UUID, SeatInterface] = {}

    def stop(self):
        for child in self._children:
            child.stop()
        self._is_running = False

    def stop_if_deserted(self) -> None:
        if not any(interface.is_connected() for interface in self.seat_map.values()):
            self.stop()

    def schedule_stop_check(self, delay: int) -> None:
        thread = Cleaner(self, delay)
        self._children.append(thread)
        thread.start()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @is_running.setter
    def is_running(self, v: bool) -> None:
        with self._lock:
            self._is_running = v

    def run(self):
        try:
            self.is_running = True

            ES.bind(EventSystem())

            gs = GameState(
                2,
                lambda *args, **kwargs: SeatInterface(*args, **kwargs, game=self),
                self._scenario.landscape,
            )

            self.seat_map: dict[UUID, SeatInterface] = {
                seat.id: connection
                for (player, connection), seat in zip(
                    gs.connections.items(), self._game.seats
                )
            }

            GS.bind(gs)

            GM.register(self)

            for player, units in zip(gs.turn_order.players, self._scenario.units):
                for cc, blueprint in units.items():
                    ES.resolve(
                        SpawnUnit(
                            blueprint=blueprint,
                            controller=player,
                            space=gs.map.hexes[cc],
                        )
                    )

            for logs in gs._pending_player_logs.values():
                logs[:] = []

            ES.resolve(Play())
        except GameClosed:
            pass
        except:
            traceback.print_exc()
            raise
        finally:
            self.is_running = False
            GM.deregister(self)

        print("game finished")
