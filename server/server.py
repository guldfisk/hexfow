from __future__ import annotations

import json
import random
import threading
import traceback
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Mapping, Any

from websockets import ConnectionClosed
from websockets.sync.server import serve, ServerConnection

from events.eventsystem import ES, EventSystem
from events.exceptions import GameException
from game.game.core import GameState, Landscape
from game.game.events import SpawnUnit, Play
from game.game.interface import Connection
from game.game.map.coordinates import CC
from game.game.map.geometry import hex_circle
from game.game.map.terrain import Plains, Forest, Magma, Water
from game.game.player import Player
from game.game.units.blueprints import *


class GameClosed(GameException):
    pass


class GameManager:
    def __init__(self):
        self._running: list[Game] = []
        self._lock = threading.Lock()

    def register(self, game: Game) -> None:
        with self._lock:
            self._running.append(game)

    def deregister(self, game: Game) -> None:
        with self._lock:
            self._running.remove(game)

    def stop_all(self) -> None:
        with self._lock:
            for game in self._running:
                game.stop()


GM = GameManager()


class Game(Thread):
    def __init__(self, connection: ServerConnection):
        super().__init__()
        self._lock = threading.Lock()
        self._is_running = False
        self.in_queue = SimpleQueue()
        self.connection = connection

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
            GM.register(self)

            ES.bind(EventSystem())

            game = self

            class WebsocketConnection(Connection):
                def __init__(self, player: Player):
                    super().__init__(player)

                def send(self, values: Mapping[str, Any]) -> None:
                    # game.out_queue.put(values)
                    # raise NotImplemented()
                    pass

                def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
                    # print(values)
                    game.connection.send(json.dumps(values))
                    while game.is_running:
                        try:
                            response = game.in_queue.get(timeout=1)
                            return response
                        except Empty:
                            pass
                    raise GameClosed()

            gs = GameState(
                2,
                WebsocketConnection,
                Landscape(
                    {
                        cc: random.choice(
                            [
                                # Plains,
                                Forest,
                                Magma,
                                # Water,
                            ]
                        )
                        for cc in hex_circle(7)
                    }
                ),
            )
            GameState.instance = gs

            ccs = sorted(
                gs.map.hexes.keys(),
                key=lambda cc: (cc.distance_to(CC(0, 0)), cc.r, CC.h),
            )

            for player, values in (
                (
                    gs.turn_order.players[0],
                    (
                        GOBLIN_ASSASSIN,
                        PESTILENCE_PRIEST,
                        # LOTUS_BUD,
                        # DIRE_WOLF,
                        # DIRE_WOLF,
                        DIRE_WOLF,
                        LOTUS_BUD,
                        BULLDOZER,
                        CHAINSAW_SADIST,
                        # GNOME_COMMANDO,
                        # (BOULDER_HURLER_OAF, CC(0, 0)),
                        # RHINO_BEAST,
                        CHICKEN,
                        MARSHMALLOW_TITAN,
                        MEDIC,
                        ZONE_SKIRMISHER,
                        # CYCLOPS,
                        BLITZ_TROOPER,
                    ),
                ),
                (
                    gs.turn_order.players[1],
                    (
                        WAR_HOG,
                        LIGHT_ARCHER,
                        # BUGLING,
                        # CYCLOPS,
                        # CYCLOPS,
                        # BULLDOZER,
                        LIGHT_ARCHER,
                        LOTUS_BUD,
                        GNOME_COMMANDO,
                        # WAR_HOG,
                        # (LIGHT_ARCHER, CC(0, 1)),
                        # CYCLOPS,
                        LUMBERING_PILLAR,
                        AP_GUNNER,
                        CACTUS,
                        CHICKEN,
                        CHAINSAW_SADIST,
                        # SCARAB,
                        PESTILENCE_PRIEST,
                    ),
                ),
            ):
                for v in values:
                    if isinstance(v, tuple):
                        blueprint, cc = v
                        print(cc, ccs)
                        ccs.remove(cc)
                        ES.resolve(
                            SpawnUnit(
                                blueprint=blueprint,
                                controller=player,
                                space=gs.map.hexes[cc],
                            )
                        )
                    else:
                        ES.resolve(
                            SpawnUnit(
                                blueprint=v,
                                controller=player,
                                space=gs.map.hexes[ccs.pop(0)],
                            )
                        )

            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=BOULDER_HURLER_OAF,
            #         controller=gs.turn_order.players[0],
            #         space=gs.map.hexes[CC(0, 0)],
            #     )
            # )
            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=LUMBERING_PILLAR,
            #         controller=gs.turn_order.players[0],
            #         space=gs.map.hexes[CC(1, -1)],
            #     )
            # )
            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=LIGHT_ARCHER,
            #         controller=gs.turn_order.players[0],
            #         space=gs.map.hexes[CC(1, 0)],
            #     )
            # )
            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=BUGLING,
            #         controller=gs.turn_order.players[0],
            #         space=gs.map.hexes[CC(0, 0)],
            #     )
            # )
            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=CYCLOPS,
            #         controller=gs.turn_order.players[0],
            #         space=gs.map.hexes[CC(-1, 0)],
            #     )
            # )

            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=LIGHT_ARCHER,
            #         controller=gs.turn_order.players[1],
            #         space=gs.map.hexes[CC(0, -1)],
            #     )
            # )
            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=AP_GUNNER,
            #         controller=gs.turn_order.players[1],
            #         space=gs.map.hexes[CC(0, -2)],
            #     )
            # )
            # ES.resolve(
            #     SpawnUnit(
            #         blueprint=CACTUS,
            #         controller=gs.turn_order.players[1],
            #         space=gs.map.hexes[CC(-1, 1)],
            #     )
            # )

            ES.resolve(Play())
        except GameClosed:
            pass
        except:
            traceback.print_exc()
            raise
        finally:
            self.is_running = False
            GM.deregister(self)


def handle_connection(connection: ServerConnection) -> None:
    print("connected")
    game = Game(connection)
    game.start()
    while game.is_running:
        try:
            game.in_queue.put(json.loads(connection.recv(timeout=1)))
        except TimeoutError:
            pass
        except ConnectionClosed:
            game.stop()
            break
        except:
            traceback.print_exc()
            raise
    print("connection closed")


def main():
    print("running server")
    try:
        # with serve(handle_connection, "localhost", 8765) as server:
        with serve(handle_connection, "0.0.0.0", 8765) as server:
            server.serve_forever()
    except:
        GM.stop_all()
        raise


if __name__ == "__main__":
    main()
