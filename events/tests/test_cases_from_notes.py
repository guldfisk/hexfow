from __future__ import annotations

import dataclasses
from typing import ClassVar

import pytest

from events.eventsystem import (
    ReplacementEffect,
    StateModifierEffect,
    ES,
)
from events.tests.game_objects.advanced_units import (
    Map,
    Hex,
    Unit,
    Move,
    Kill,
    Heal,
)


@pytest.fixture
def ground_map() -> Map:
    return Map([Hex() for _ in range(3)])


def test_unit_crushed(ground_map: Map):
    units = [Unit() for _ in range(2)]
    for unit, _hex in zip(units, ground_map.hexes):
        ES.resolve(Move(unit, ground_map, _hex))

    ES.resolve(Move(units[1], ground_map, ground_map.hexes[2]))
    assert ground_map.get_position_off(units[1]) == ground_map.hexes[2]

    ES.resolve(Move(units[0], ground_map, ground_map.hexes[2]))
    assert ground_map.get_position_off(units[0]) == ground_map.hexes[0]

    class Crushable(ReplacementEffect[Move]):
        priority = 1

        def resolve(self, event: Move) -> None:
            if existing_unit := event.to.unit:
                ES.resolve(Kill(existing_unit))
                ES.resolve(Heal(event.unit, 2))
                event.to.unit = None
            ES.resolve(event)

    ES.register_effect(Crushable())

    ES.resolve(Move(units[0], ground_map, ground_map.hexes[2]))
    assert ground_map.get_position_off(units[0]) == ground_map.hexes[2]
    assert ground_map.get_position_off(units[1]) is None
    assert units[0].health == 12
    assert units[1].health == 0


def test_pathing_selectively_blocked(ground_map: Map):
    units = [Unit() for _ in range(2)]
    for unit, _hex in zip(units, ground_map.hexes):
        ES.resolve(Move(unit, ground_map, _hex))

    for _hex, target in zip(ground_map.hexes, (False, False, True)):
        assert _hex.can_move_into(units[0]) is target

    @dataclasses.dataclass
    class PositionJoinable(StateModifierEffect[Hex, Unit, bool]):
        priority: ClassVar[int] = 1
        target: ClassVar[object] = Hex.is_occupied_for

        unit: Unit

        def should_modify(self, obj: Hex, request: Unit, value: bool) -> bool:
            return obj.unit == self.unit

        def modify(self, obj: Hex, request: Unit, value: bool) -> bool:
            return True

    ES.register_effect(PositionJoinable(units[1]))

    for _hex, target in zip(ground_map.hexes, (False, True, True)):
        assert _hex.can_move_into(units[0]) is target
