from typing import Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from game.core import UnitBlueprint, Terrain, Status, Facet
from game.map import terrain  # noqa F401
from game.units import blueprints  # noqa F401


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
