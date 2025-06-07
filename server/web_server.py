from typing import Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from game.game.core import UnitBlueprint, Terrain, Status, UnitStatus
from game.game.map import terrain
from game.game.units import blueprints
from game.game import statuses

unit_blueprint = [
    v for v in blueprints.__dict__.values() if isinstance(v, UnitBlueprint)
]
terrains = [
    v
    for v in terrain.__dict__.values()
    if isinstance(v, type) and issubclass(v, Terrain) and v != Terrain
]
unit_statuses = [
    v
    for v in statuses.__dict__.values()
    if isinstance(v, type) and issubclass(v, UnitStatus) and v != UnitStatus
]


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://0.0.0.0:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get():
    return {"status": "ok"}


@app.get("/game-object-details")
async def get_game_object_details() -> dict[str, Any]:
    return {
        "units": {
            unit.identifier: {
                "identifier": unit.identifier,
                "name": unit.name,
                "small_image": f"/src/images/{unit.identifier}_small.png",
            }
            for unit in unit_blueprint
        },
        "terrain": {
            _terrain.identifier: {
                "identifier": _terrain.identifier,
                "name": _terrain.__name__,
                "image": f"/src/images/terrain_{_terrain.identifier}_square.png",
            }
            for _terrain in terrains
        },
        "statuses": {
            status.identifier: {
                "identifier": status.identifier,
                "name": status.__name__,
                "image": f"/src/images/statuses/{status.identifier}.png",
            }
            for status in unit_statuses
        },
    }
