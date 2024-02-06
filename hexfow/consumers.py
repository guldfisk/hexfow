import time
from threading import Thread

from channels.generic.websocket import JsonWebsocketConsumer

from game.game.map.hexmap import generate_super_map


class GameConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        self.send_json(generate_super_map().serialize())
        self.is_connected = True
        print('CONNECT')

        # def _worker():
        #     while self.is_connected:
        #         self.send_json(generate_super_map().serialize())
        #         time.sleep(1)
        #
        # self.worker = Thread(target=_worker)
        # self.worker.start()

    def disconnect(self, close_code):
        self.is_connected = False
