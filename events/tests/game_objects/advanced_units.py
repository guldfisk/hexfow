from __future__ import annotations

import dataclasses
from enum import Enum, auto

from events.eventsystem import (
    Event,
    ModifiableAttribute,
    Modifiable,
    modifiable, ES,
)


class TerrainType(Enum):
    GROUND = auto()
    WATER = auto()


class Player: ...


# @dataclasses.dataclass
class Unit(Modifiable):
    power: ModifiableAttribute[None, int]
    toughness: ModifiableAttribute[None, int]
    flying: ModifiableAttribute[None, bool]

    # def __hash__(self):
    #     return id(self)
    #
    # def __eq__(self, other):
    #     return self is other

    def __init__(
        self,
        # position: Hex,
        power: int = 1,
        toughness: int = 1,
        flying: bool = False,
        controller: Player | None = None,
    ):
        # self.position = position
        self.power.set(power)
        self.toughness.set(toughness)
        self.health = 10
        self.flying.set(flying)
        self.controller = controller


class Hex(Modifiable):

    def __init__(self, terrain_type: TerrainType = TerrainType.GROUND):
        self.terrain_type = terrain_type
        self.unit: Unit | None = None

    @modifiable
    def is_passable_to(self, unit: Unit) -> bool:
        return self.terrain_type == TerrainType.GROUND or unit.flying.get(None)

    @modifiable
    def is_occupied_for(self, unit: Unit) -> bool:
        return not self.unit

    @modifiable
    def can_move_into(self, unit: Unit) -> bool:
        return self.is_occupied_for(unit) and self.is_passable_to(unit)


class Map:

    def __init__(self, hexes: list[Hex]):
        self.hexes = hexes

    def get_position_off(self, unit: Unit) -> Hex | None:
        for _hex in self.hexes:
            if unit == _hex.unit:
                return _hex


@dataclasses.dataclass
class ChangePosition(Event[None]):
    unit: Unit
    # TODO Also need to solve
    map: Map
    to: Hex

    def resolve(self) -> None:
        if previous_hex := self.map.get_position_off(self.unit):
            previous_hex.unit = None
        self.to.unit = self.unit


@dataclasses.dataclass
class Move(Event[Hex | None]):
    unit: Unit
    # TODO Also need to solve
    map: Map
    to: Hex

    def resolve(self) -> Hex | None:
        if not self.to.unit:
            ES.resolve(self.branch(ChangePosition))
            return self.to


@dataclasses.dataclass
class Heal(Event[None]):
    unit: Unit
    amount: int

    def resolve(self) -> None:
        self.unit.health += self.amount


@dataclasses.dataclass
class Kill(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        self.unit.health = 0
