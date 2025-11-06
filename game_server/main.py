from __future__ import annotations

import json
import traceback
from uuid import UUID

from websockets import ConnectionClosed
from websockets.sync.server import ServerConnection, serve

from game.map import terrain  # noqa F401
from game.statuses import hex_statuses, unit_statuses  # noqa F401
from game.units import blueprince  # noqa F401
from game_server.games import GM
from game_server.testing import TestGameRunner


def handle_test_connection(connection: ServerConnection) -> None:
    test_runner = TestGameRunner(connection)
    test_runner.start()
    while test_runner.is_running:
        try:
            test_runner.in_queue.put(json.loads(connection.recv(timeout=1)))
        except TimeoutError:
            pass
        except ConnectionClosed:
            test_runner.stop()
            break
        except:
            traceback.print_exc()
            raise


def handle_seat_connection(connection: ServerConnection, seat_id: UUID) -> None:
    interface = GM.get_seat_interface(seat_id)
    interface.register_callback(connection.send)

    while interface.game_runner.is_running:
        try:
            interface.in_queue.put(json.loads(connection.recv(timeout=1)))
        except TimeoutError:
            pass
        except ConnectionClosed:
            break
        except:
            traceback.print_exc()
            raise
    interface.deregister_callback(connection.send)
    interface.game_runner.schedule_stop_check(60)


def handle_connection(connection: ServerConnection) -> None:
    print("connected")

    seat_id = json.loads(connection.recv())["seat_id"]

    if seat_id == "test":
        handle_test_connection(connection)
    else:
        handle_seat_connection(connection, UUID(seat_id))

    print("connection closed")


def main():
    print("running server")
    try:
        with serve(handle_connection, "0.0.0.0", 8765) as server:
            server.serve_forever()
    except:
        GM.stop_all()
        raise


if __name__ == "__main__":
    main()
