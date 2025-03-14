from __future__ import  annotations

import dataclasses
from typing import Any

import pytest

from debug_utils import dp
from events.eventsystem import (
    EventSystem,
    ReplacementEffect,
    E,
    WithModifiableAttributes,
)
from events.tests.game_objects.advanced_units import (
    Map,
    Hex,
    Unit,
    Move,
    Kill,
    Heal,
    TerrainType,
)


@pytest.fixture
def ground_map() -> Map:
    return Map([Hex() for _ in range(3)])


def test_unit_crushed(es: EventSystem, ground_map: Map):
    units = [Unit() for _ in range(2)]
    for unit, _hex in zip(units, ground_map.hexes):
        es.resolve(Move(unit, ground_map, _hex))

    es.resolve(Move(units[1], ground_map, ground_map.hexes[2]))
    assert ground_map.get_position_off(units[1]) == ground_map.hexes[2]

    es.resolve(Move(units[0], ground_map, ground_map.hexes[2]))
    assert ground_map.get_position_off(units[0]) == ground_map.hexes[0]

    class Crushable(ReplacementEffect[Move]):
        priority = 1

        def resolve(self, es: EventSystem, event: Move) -> None:
            if existing_unit := event.to.unit:
                es.resolve(Kill(existing_unit))
                es.resolve(Heal(event.unit, 2))
                event.to.unit = None
            es.resolve(event)

    es.register_effect(Crushable())

    es.resolve(Move(units[0], ground_map, ground_map.hexes[2]))
    assert ground_map.get_position_off(units[0]) == ground_map.hexes[2]
    assert ground_map.get_position_off(units[1]) is None
    assert units[0].health == 12
    assert units[1].health == 0


def test_pathing_selectively_blocked(es: EventSystem):

    class SomeShit:
        v: int = 7

        def __call__(self: IDK, *args, **kwargs):
            return 1 + self.value

    def deco(f):
        # return SomeShit()
        def wrapper(self: IDK, *args, **kwargs):
            return self.value + 1
            # return f(*args, **kwargs)
        return wrapper

    @dataclasses.dataclass
    class IDK(WithModifiableAttributes):
        value: int

        @deco
        def whatever(self, a: int) -> Any: ...

    assert IDK(1).whatever(10) == 2
    # assert IDK().whatever.v
