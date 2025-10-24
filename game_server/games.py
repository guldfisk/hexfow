from __future__ import annotations

import json
import threading
import time
import traceback
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Any, Callable, Iterator, Mapping
from uuid import UUID

from sqlalchemy import Exists, select

from events.eventsystem import ES
from game.core import Connection, DecisionPoint, G_decision_result, Player
from game.events import Play
from game_server.exceptions import GameClosed
from game_server.game_types import GameType
from game_server.setup import setup_scenario, setup_scenario_units
from model.engine import SS
from model.models import Game, Seat


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
    def __init__(self, player: Player, game_runner: GameRunner):
        super().__init__(player)
        self.game_runner = game_runner
        self._latest_game_state_frame = None
        self._latest_game_state_frame_lock = threading.Lock()
        self._lock = threading.Lock()
        self.in_queue = SimpleQueue()
        self._callbacks: list[Callable[[str], ...]] = []

        self._remaining_time: float = game_runner.game.time_bank or 0
        self._grace: float = game_runner.game.time_grace or 0

    def _send_frame_to_callback(
        self, f: Callable[[str], ...], values: Mapping[str, Any]
    ) -> None:
        try:
            f(json.dumps(values))
        except Exception:
            print(traceback.format_exc())
            self._callbacks.remove(f)

    def register_callback(self, f: Callable[[str], ...]) -> None:
        with self._lock:
            self._callbacks.append(f)
            with self._latest_game_state_frame_lock:
                if self._latest_game_state_frame is not None:
                    self._send_frame_to_callback(f, self._latest_game_state_frame)

    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._callbacks)

    def deregister_callback(self, f: Callable[[str], ...]) -> None:
        with self._lock:
            try:
                self._callbacks.remove(f)
            except (IndexError, ValueError):
                pass

    def make_game_state_frame(
        self, game_state: Mapping[str, Any], decision_point: DecisionPoint | None = None
    ) -> dict[str, Any]:
        frame = {
            "message_type": "game_state",
            "count": self._game_state_counter,
            "game_state": game_state,
            **(
                {"remaining_time": self._remaining_time, "grace": self._grace - 0.5}
                if self.game_runner.game.time_bank is not None
                else {}
            ),
        }
        with self._latest_game_state_frame_lock:
            self._latest_game_state_frame = frame
            return frame

    def send(self, values: Mapping[str, Any]) -> None:
        with self._lock:
            for f in list(self._callbacks):
                self._send_frame_to_callback(f, values)

    def wait_for_response(self) -> Iterator[G_decision_result | None]:
        start_time = time.time()
        while self.game_runner.is_running:
            try:
                if (
                    validated := self.validate_decision_message(
                        self.in_queue.get(timeout=0.01)
                    )
                ) is not None:
                    if self.game_runner.game.time_bank is not None:
                        self._remaining_time -= max(
                            (time.time() - start_time) - self._grace, 0
                        )
                    yield validated
                    return
            except Empty:
                if (
                    self.game_runner.game.time_bank is not None
                    and time.time() - start_time > self._remaining_time + self._grace
                ):
                    self.game_runner.send_result_message(
                        [
                            interface
                            for interface in self.game_runner.seat_map.values()
                            if interface != self
                        ][0].player.name,
                        "opponent timeout",
                    )
                    self.game_runner.stop()
            yield None
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
        self._scenario = (
            GameType.registry[game.game_type]
            .model_validate(game.settings)
            .get_scenario()
        )
        self.game = game
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
            print("cleaning up deserted game")
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

    def send_result_message(self, winner: str, result: str) -> None:
        for interface in self.seat_map.values():
            interface.send(
                {"message_type": "game_result", "winner": winner, "reason": result}
            )

    def run(self):
        try:
            self.is_running = True

            gs = setup_scenario(
                self._scenario,
                lambda player: SeatInterface(player, game_runner=self),
            )

            self.seat_map: dict[UUID, SeatInterface] = {
                seat.id: connection
                for (player, connection), seat in zip(
                    gs.connections.items(), self.game.seats
                )
            }
            GM.register(self)

            setup_scenario_units(
                self._scenario,
                with_fow=self.game.with_fow,
                custom_armies=self.game.custom_armies,
            )

            if (
                len(winners := [e.result for e in ES.resolve(Play()).iter_type(Play)])
                == 1
            ):
                self.send_result_message(winners[0].name, "having the most points")
        except GameClosed:
            pass
        except:
            traceback.print_exc()
            raise
        finally:
            self.is_running = False
            GM.deregister(self)

        print("game finished")
