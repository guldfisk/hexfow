from __future__ import annotations

import json
import threading
import traceback
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Any, Mapping

from websockets import ServerConnection

from events.eventsystem import ES, EventSystem
from game.core import Connection, Player
from game.events import Play
from game_server.game_types import TestGameType
from game_server.setup import setup_scenario


class TestGameRunner(Thread):
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

    def start(self):
        self.is_running = True
        super().start()

    def run(self):
        try:
            ES.bind(EventSystem())

            game = self

            class WebsocketConnection(Connection):
                def __init__(self, player: Player):
                    super().__init__(player)

                def send(self, values: Mapping[str, Any]) -> None:
                    pass

                def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
                    game.connection.send(json.dumps(values))
                    while game.is_running:
                        try:
                            response = game.in_queue.get(timeout=1)
                            return response
                        except Empty:
                            pass
                    raise ValueError("game closed")

            setup_scenario(
                TestGameType().get_scenario(),
                lambda player: WebsocketConnection(player),
            )

            ES.resolve(Play())
        except:
            traceback.print_exc()
            raise
        finally:
            self.is_running = False
