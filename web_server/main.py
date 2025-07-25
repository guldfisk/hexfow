import os
from typing import Any, Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Depends
from starlette.middleware.cors import CORSMiddleware

from game.core import UnitBlueprint, Terrain, Status, Facet
from game.map import terrain  # noqa F401
from game.units import blueprints  # noqa F401
from model.engine import SS
from model.models import Game, Seat
from web_server.schemas import CreateGameSchema

load_dotenv()

HOST_NAME = os.environ.get("HOST")

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://0.0.0.0:5173",
] + (
    [
        f"http://{HOST_NAME}",
        f"http://{HOST_NAME}:5173",
    ]
    if HOST_NAME
    else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _session() -> Iterator[None]:
    """
    Wrap all views in a transaction, commited or rolled back if there
    is an exception.
    """
    try:
        yield
        SS.commit()
    except:
        SS.remove()
        raise


top_router = APIRouter(dependencies=[Depends(_session)])


@top_router.get("/")
async def get():
    return {"status": "ok"}


@top_router.get("/game-object-details")
async def get_game_object_details() -> dict[str, Any]:
    return {
        "units": {
            unit.identifier: unit.serialize()
            for unit in UnitBlueprint.registry.values()
        },
        "terrain": {
            _terrain.identifier: _terrain.serialize_type()
            for _terrain in Terrain.registry.values()
        },
        "statuses": {
            status.identifier: status.serialize_type()
            for status in Status.registry.values()
        },
        "facets": {
            facet.identifier: facet.serialize_type()
            for facet in Facet.registry.values()
        },
    }


@top_router.post("/create-game")
def create_game(body: CreateGameSchema) -> dict[str, Any]:
    game = Game(
        game_type=body.game_type,
        seats=[Seat(position=i, player_name=f"player {i}") for i in range(1, 3)],
    )
    SS.add(game)
    SS.flush()
    return {
        "seats": [
            {"id": seat.id, "position": seat.position, "player_name": seat.player_name}
            for seat in game.seats
        ]
    }


app.include_router(top_router)
