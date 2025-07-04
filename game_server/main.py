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
from game.core import GameState, Landscape, HexSpec
from game.events import SpawnUnit, Play
from game.interface import Connection
from game.map.coordinates import CC, cc_to_rc, NEIGHBOR_OFFSETS
from game.map.geometry import hex_circle
from game.map.terrain import Plains, Forest, Magma, Hills, Water, Shrubs
from game.player import Player
from game.units.blueprints import *


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

            # random.seed(23947)

            gs = GameState(
                2,
                WebsocketConnection,
                Landscape(
                    {
                        cc: HexSpec(
                            random.choice(
                                # [
                                #     # Water,
                                #     # Plains,
                                #     Shrubs,
                                #     # Magma,
                                # ]
                                [
                                    Plains,
                                    Plains,
                                    Plains,
                                    # Shrubs,
                                    Forest,
                                    Forest,
                                    # Magma,
                                    # Plains,
                                    # Plains,
                                    # Plains,
                                    # Forest,
                                    # Forest,
                                    # Forest,
                                ]
                            ),
                            cc.distance_to(CC(0, 0)) <= 1,
                        )
                        for cc in hex_circle(4)
                    }
                ),
            )
            GameState.instance = gs

            player_units = (
                (
                    INK_WITCH,
                    BOMBARD_CANON,
                    # LIGHT_ARCHER,
                    # WITCH_ENGINE,
                    # INFERNO_TANK,
                    MAD_SCIENTIST,
                    # INFERNO_TANK,
                    # DOOMBOT_3000,
                ),
                (
                    CYCLOPS,
                    # LIGHT_ARCHER,
                    WITCH_ENGINE,
                    # ZONE_SKIRMISHER,
                    # INFERNO_TANK,
                ),
            )

            use_random_units = False
            # use_random_units = True

            if use_random_units:
                min_random_unit_quantity = 7
                random_unt_quantity_threshold = 12
                point_threshold = random_unt_quantity_threshold * 5
                banned_units = {LOTUS_BUD, CACTUS, DIAMOND_GOLEM}

                unit_pool = [
                    blueprint
                    for blueprint in UnitBlueprint.registry.values()
                    for _ in range(blueprint.max_count)
                    if blueprint.price is not None and not blueprint in banned_units
                ]
                random.shuffle(unit_pool)

                player_units = [[], []]

                while (
                    any(len(us) < min_random_unit_quantity for us in player_units)
                    or any(
                        sum(u.price for u in us) < point_threshold
                        for us in player_units
                    )
                ) and not any(
                    len(us) > random_unt_quantity_threshold for us in player_units
                ):
                    min(player_units, key=lambda v: sum(u.price for u in v)).append(
                        unit_pool.pop()
                    )

                player_points = [sum(u.price for u in v) for v in player_units]
                if not len(set(player_points)) == 1 and unit_pool:
                    eligible_price = (
                        max(below_threshold)
                        if (
                            below_threshold := [
                                unit.price
                                for unit in unit_pool
                                if unit.price
                                <= abs(player_points[0] - player_points[1])
                            ]
                        )
                        else min(unit.price for unit in unit_pool)
                    )
                    player_units[
                        min(enumerate(player_points), key=lambda v: v[1])[0]
                    ].append(
                        random.choice(
                            [unit for unit in unit_pool if unit.price == eligible_price]
                        )
                    )

                print("points", [sum(u.price for u in v) for v in player_units])
                print("units", [len(v) for v in player_units])

                ccs = [
                    cc
                    for cc in hex_circle(3)
                    if (_hex := gs.map.hexes.get(cc)) and not _hex.terrain.is_water()
                ]
                random.shuffle(ccs)
                player_ccs = [
                    [
                        cc
                        for cc in ccs
                        if ((x := cc_to_rc(cc).x) < 1 or x > 1)
                        and (x < 0 if i else x > 0)
                    ]
                    for i in range(2)
                ]

                for player, units, pccs in zip(
                    gs.turn_order.players, player_units, player_ccs
                ):
                    for unit in units:
                        if pccs:
                            ES.resolve(
                                SpawnUnit(
                                    blueprint=unit,
                                    controller=player,
                                    space=gs.map.hexes[pccs.pop()],
                                )
                            )
                        else:
                            print("RAN OUT OF SPACE FOR", unit, ":(")

                # for idx, player in enumerate(gs.turn_order.players):
                #     for cc in ccs[
                #         idx * random_unit_quantity : (idx + 1) * random_unit_quantity
                #         + 1
                #     ]:
                #         ES.resolve(
                #             SpawnUnit(
                #                 blueprint=random.choice(
                #                     list(UnitBlueprint.registry.values())
                #                 ),
                #                 controller=player,
                #                 space=gs.map.hexes[cc],
                #             )
                #         )

            else:
                ccs = sorted(
                    gs.map.hexes.keys(),
                    key=lambda cc: (cc.distance_to(CC(0, 0)), cc.r, CC.h),
                )
                for player, values in zip(gs.turn_order.players, player_units):
                    for v in values:
                        if isinstance(v, tuple):
                            blueprint, cc = v
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

            # for player in gs.turn_order.players:
            #     for idx, unit in enumerate(gs.map.units_controlled_by(player)):
            #         unit.damage = 2 * idx
            #         unit.energy -= 3 * idx

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
