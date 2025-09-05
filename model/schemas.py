from typing import Literal

from pydantic import BaseModel

from game.core import (
    HexSpec,
    HexStatus,
    HexStatusSignature,
    Landscape,
    Scenario,
    Terrain,
    UnitBlueprint,
)
from game.map.coordinates import CC


# TODO where?
class CCSchema(BaseModel):
    r: int
    h: int

    def get_cc(self) -> CC:
        return CC(self.r, self.h)


class UnitSchema(BaseModel):
    identifier: str
    allied: bool


class HexSchema(BaseModel):
    cc: CCSchema
    terrain_type: str
    is_objective: bool
    deployment_zone_of: Literal[0, 1, None]
    statuses: list[str]
    unit: UnitSchema | None

    def get_hex_spec(self) -> tuple[CC, HexSpec]:
        return self.cc.get_cc(), HexSpec(
            Terrain.get_class(self.terrain_type),
            is_objective=self.is_objective,
            deployment_zone_of=self.deployment_zone_of,
            statuses=[
                HexStatusSignature(HexStatus.get_class(status_identifier), None)
                for status_identifier in self.statuses
            ],
        )


class ScenarioSchema(BaseModel):
    hexes: list[HexSchema]

    def get_scenario(self) -> Scenario:
        return Scenario(
            landscape=Landscape(
                dict(hex_schema.get_hex_spec() for hex_schema in self.hexes)
            ),
            units=[
                {
                    hex_schema.cc.get_cc(): UnitBlueprint.get_class(
                        hex_schema.unit.identifier
                    )
                    for hex_schema in self.hexes
                    if hex_schema.unit and hex_schema.unit.allied is allied
                }
                for allied in (False, True)
            ],
        )
