from __future__ import annotations

import json
import random
import threading
import traceback
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Mapping, Any, Callable
from uuid import UUID

from sqlalchemy import select, Exists
from websockets import ConnectionClosed
from websockets.sync.server import serve, ServerConnection

from events.eventsystem import ES, EventSystem
from events.exceptions import GameException
from game.core import GameState, Landscape, HexSpec, GS
from game.events import SpawnUnit, Play
from game.interface import Connection
from game.map.coordinates import CC, cc_to_rc, NEIGHBOR_OFFSETS
from game.map.geometry import hex_circle
from game.map.terrain import Plains, Forest, Magma, Hills, Water, Shrubs
from game.player import Player
from game.units.blueprints import *
from game_server.scenarios import get_test_scenario, get_simple_scenario
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


class GameRunner(Thread):
    # def __init__(self, seats: list[Seat]):
    def __init__(self, game: Game):
        super().__init__()
        self._scenario = get_simple_scenario()
        self._game = game
        # self.seats = seats
        self._lock = threading.Lock()
        self._is_running = False

        self.gs = GameState(
            2,
            lambda *args, **kwargs: SeatInterface(*args, **kwargs, game=self),
            self._scenario.landscape,
            # Landscape(
            #     {
            #         cc: HexSpec(
            #             random.choice([Plains, Forest]),
            #             cc.distance_to(CC(0, 0)) <= 1,
            #         )
            #         for cc in hex_circle(4)
            #     }
            # ),
        )

        self.seat_map: dict[UUID, SeatInterface] = {
            seat.id: connection
            for (player, connection), seat in zip(
                self.gs.connections.items(), self._game.seats
            )
        }

    def stop(self):
        self._is_running = False

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
            GS.bind(self.gs)

            GM.register(self)

            # player_units = (
            #     (
            #         STAUNCH_IRON_HEART,
            #         MAD_SCIENTIST,
            #         INFERNO_TANK,
            #     ),
            #     (
            #         BLOOD_CONDUIT,
            #         CYCLOPS,
            #         WITCH_ENGINE,
            #         LIGHT_ARCHER,
            #     ),
            # )
            #
            # ccs = sorted(
            #     self.gs.map.hexes.keys(),
            #     key=lambda cc: (cc.distance_to(CC(0, 0)), cc.r, CC.h),
            # )
            # for player, values in zip(self.gs.turn_order.players, player_units):
            #     for v in values:
            #         if isinstance(v, tuple):
            #             blueprint, cc = v
            #             ccs.remove(cc)
            #             ES.resolve(
            #                 SpawnUnit(
            #                     blueprint=blueprint,
            #                     controller=player,
            #                     space=self.gs.map.hexes[cc],
            #                 )
            #             )
            #         else:
            #             ES.resolve(
            #                 SpawnUnit(
            #                     blueprint=v,
            #                     controller=player,
            #                     space=self.gs.map.hexes[ccs.pop(0)],
            #                 )
            #             )

            for player, units in zip(self.gs.turn_order.players, self._scenario.units):
                for cc, blueprint in units.items():
                    ES.resolve(
                        SpawnUnit(
                            blueprint=blueprint,
                            controller=player,
                            space=self.gs.map.hexes[cc],
                        )
                    )

            for logs in self.gs._pending_player_logs.values():
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
