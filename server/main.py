import asyncio
import time
import traceback
from asyncio import sleep
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from queue import SimpleQueue, Empty
from threading import Thread
from typing import Mapping, Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from events.eventsystem import ES, EventSystem
from game.game.core import Landscape, GameState
from game.game.events import Play, Round, SpawnUnit
from game.game.interface import Connection
from game.game.map.coordinates import CC
from game.game.map.geometry import hex_circle
from game.game.player import Player
from game.game.units.blueprints import CHICKEN
from game.tests.test_events import MockConnection


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     app.state.executor = ThreadPoolExecutor()
#     app.state._loop = asyncio.get_running_loop()
#     yield
#     app.state.executor.shutdown()
#     app.state._loop.close()


app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8765/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


# class MetaGame:
#
#     def __init__(self):
#         self.is_running = False
#         self.in_queue = SimpleQueue()
#         self.out_queue = SimpleQueue()
#
#
# def run_game(meta_game: MetaGame):
#     meta_game.is_running = True
#     print("game running")
#
#     ES.bind(EventSystem())
#
#     class WebsocketConnection(Connection):
#
#         def __init__(self, player: Player):
#             super().__init__(player)
#
#         def send(self, values: Mapping[str, Any]) -> None:
#             meta_game.out_queue.put(values)
#
#         def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
#             print("get response", values)
#             meta_game.out_queue.put(values)
#             while meta_game.is_running:
#                 try:
#                     return meta_game.in_queue.get(timeout=1)
#                 except Empty:
#                     pass
#
#     gs = GameState(
#         1, WebsocketConnection, Landscape({cc: Ground for cc in hex_circle(2)})
#     )
#     GameState.instance = gs
#     print("before")
#
#     ES.resolve(
#         SpawnUnit(
#             blueprint=CHICKEN,
#             controller=gs.turn_order.players[0],
#             space=gs.map.hexes[CC(0, 0)],
#         )
#     )
#
#     ES.resolve(Round())


# class Game(Thread):
#
#     def __init__(self):
#         super().__init__(daemon=True)
#         self._is_running = False
#         self.in_queue = SimpleQueue()
#         self.out_queue = SimpleQueue()
#
#     def stop(self):
#         self._is_running = False
#
#     def run(self):
#         self._is_running = True
#         i = 0
#         while self._is_running:
#             i += 1
#             if i > 2:
#                 return
#             print("thread loop :^)")
#             self.out_queue.put({"some": "shit"})
#             time.sleep(1)
#         # try:
#         #     self._is_running = True
#         #     print("game running")
#         #
#         #     ES.bind(EventSystem())
#         #
#         #     game = self
#         #
#         #     class WebsocketConnection(Connection):
#         #
#         #         def __init__(self, player: Player):
#         #             super().__init__(player)
#         #
#         #         def send(self, values: Mapping[str, Any]) -> None:
#         #             game.out_queue.put(values)
#         #
#         #         def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
#         #             print("get response", values)
#         #             game.out_queue.put(values)
#         #             while game._is_running:
#         #                 try:
#         #                     return game.in_queue.get(timeout=1)
#         #                 except Empty:
#         #                     pass
#         #
#         #     gs = GameState(
#         #         1, WebsocketConnection, Landscape({cc: Ground for cc in hex_circle(2)})
#         #     )
#         #     GameState.instance = gs
#         #     print("before")
#         #
#         #     ES.resolve(
#         #         SpawnUnit(
#         #             blueprint=CHICKEN,
#         #             controller=gs.turn_order.players[0],
#         #             space=gs.map.hexes[CC(0, 0)],
#         #         )
#         #     )
#         #
#         #     ES.resolve(Round())
#         #     print("after")
#         # except Exception as e:
#         #     print("HALO" * 10, e)
#         #     traceback.print_exc()


# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#
#     # meta_game = MetaGame()
#     # app.state._loop.run_in_executor(app.state.executor, run_game, meta_game)
#     game = Game()
#     game.start()
#     print("game started")
#
#     try:
#         while True:
#             try:
#                 # await websocket.send_json({"idk": "real"})
#                 # await sleep(1)
#                 # await websocket.send_json(meta_game.out_queue.get(timeout=0.1))
#                 await websocket.send_json(game.out_queue.get(timeout=0.1))
#             except Empty:
#                 pass
#     except WebSocketDisconnect:
#         game.stop()
#         game.join()
#         print("----------------> GAME COMPLETED <---------------")


# @app.on_event("startup")
# async def on_startup():
#     """ Initialize the thread pool and event loop at program startup """
#     app.state.executor = ThreadPoolExecutor()
#     app.state._loop = asyncio.get_running_loop()
#
#
# @app.on_event("shutdown")
# async def on_shutdown():
#     """ Recycle resources when the program is shut down """
#     app.state.executor.shutdown()
#     app.state._loop.close()
