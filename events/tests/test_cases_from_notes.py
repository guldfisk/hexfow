from __future__ import annotations

import dataclasses
from typing import ClassVar

import pytest

from events.eventsystem import (
    ES,
    EffectSet,
    Event,
    ReplacementEffect,
    StateModifierEffect,
    TriggerEffect,
    V,
    hook_on,
)
from events.tests.game_objects.advanced_units import (
    Charge,
    Damage,
    Heal,
    Hex,
    Kill,
    LoseHealth,
    Map,
    Move,
    PowerModifier,
    Unit,
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

    ES.register_effects(Crushable())

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

    @dataclasses.dataclass(eq=False)
    class PositionJoinable(StateModifierEffect[Hex, Unit, bool]):
        priority: ClassVar[int] = 1
        target: ClassVar[object] = Hex.is_occupied_for

        unit: Unit

        def should_modify(self, obj: Hex, request: Unit, value: bool) -> bool:
            return obj.unit == self.unit

        def modify(self, obj: Hex, request: Unit, value: bool) -> bool:
            return True

    ES.register_effects(PositionJoinable(units[1]))

    for _hex, target in zip(ground_map.hexes, (False, True, True)):
        assert _hex.can_move_into(units[0]) is target


def test_manually_trigger_events():
    unit = Unit()

    class DamageOnCharge(TriggerEffect[Charge]):
        priority = 1

        def resolve(self, event: Move) -> None:
            ES.resolve(Damage(unit=event.unit, amount=1))

    trigger_effects = [DamageOnCharge() for _ in range(2)]
    ES.register_effects(*trigger_effects)

    ES.resolve(Charge(unit, 3))
    ES.resolve_pending_triggers()

    assert unit.energy == 3
    assert unit.health == 8

    ES.check_triggers_against(Charge(unit, 10), EffectSet(trigger_effects[:1]))
    ES.resolve_pending_triggers()

    assert unit.energy == 3
    assert unit.health == 7

    ES.check_triggers_against(
        Charge(unit, 10), EffectSet([DamageOnCharge() for _ in range(3)])
    )
    ES.resolve_pending_triggers()

    assert unit.energy == 3
    assert unit.health == 4


def test_once_per_turn_replacement():
    units = [Unit() for _ in range(2)]

    class Turn(Event[None]):
        def resolve(self) -> None:
            for i in range(1, 3):
                for unit in units:
                    ES.resolve(Charge(unit, i))

    class ChargeCausesDamageOncePerTurn(ReplacementEffect[Charge]):
        priority: ClassVar[int] = 1

        def __init__(self, unit: Unit):
            self.unit = unit
            self.exhausted = False

        @hook_on(Turn)
        def on_turn_start(self, event: Turn) -> None:
            self.exhausted = False

        def can_replace(self, event: Charge) -> bool:
            return event.unit == self.unit and not self.exhausted

        def resolve(self, event: Charge) -> None:
            self.exhausted = True
            ES.resolve(event)
            ES.resolve(event.branch(Damage))

    ES.register_effect(ChargeCausesDamageOncePerTurn(units[1]))

    for _ in range(2):
        ES.resolve(Turn())

    assert units[0].energy == 6
    assert units[0].health == 10

    assert units[1].energy == 6
    assert units[1].health == 8


def test_attribute_modifier_suppressed():
    class AddPower(PowerModifier):
        priority = 0

        def modify(self, obj: Unit, request: None, value: int) -> int:
            return value + 1

    class DoublePower(PowerModifier):
        priority = 1

        def should_modify(self, obj: Unit, request: None, value: int) -> V:
            return not obj.broken.g()

        def modify(self, obj: Unit, request: None, value: int) -> int:
            return value * 2

    class Break(StateModifierEffect[Unit, None, bool]):
        priority = 2
        target = Unit.broken

        def modify(self, obj: Unit, request: None, value: bool) -> bool:
            return True

    unit = Unit(power=2)

    ES.register_effects(DoublePower(unit), AddPower(unit))
    assert unit.power.g() == 6

    ES.register_effect(Break())
    assert unit.power.g() == 3


def test_trigger_dependent_on_result_of_event():
    @dataclasses.dataclass(eq=False)
    class SharedPain(TriggerEffect[Damage]):
        priority: ClassVar[int] = 0

        from_: Unit
        to_: Unit

        def should_trigger(self, event: Damage) -> bool:
            return event.unit == self.from_

        def resolve(self, event: Damage) -> None:
            ES.resolve(
                Damage(self.to_, sum(e.result for e in event.iter_type(LoseHealth)))
            )

    units = Unit(health=4), Unit(health=10)

    ES.resolve(Damage(units[0], 1))
    assert units[0].health == 3
    assert units[1].health == 10

    ES.register_effect(SharedPain(*units))
    ES.resolve(Damage(units[0], 2))
    ES.resolve_pending_triggers()
    assert units[0].health == 1
    assert units[1].health == 8

    ES.resolve(Damage(units[0], 2))
    ES.resolve_pending_triggers()
    assert units[0].health == 0
    assert units[1].health == 7


def test_trigger_condition_dependent_on_result_of_event():
    @dataclasses.dataclass(eq=False)
    class HealFromExcessDamage(TriggerEffect[Damage]):
        priority: ClassVar[int] = 0

        unit: Unit

        def should_trigger(self, event: Damage) -> bool:
            return (
                event.unit == self.unit
                and sum(e.result for e in event.iter_type(LoseHealth)) < event.amount
            )

        def resolve(self, event: Damage) -> None:
            ES.resolve(Heal(self.unit, 3))

    unit = Unit(health=4)
    ES.register_effect(HealFromExcessDamage(unit))

    ES.resolve(Damage(unit, 3))
    ES.resolve_pending_triggers()
    assert unit.health == 1

    ES.resolve(Damage(unit, 3))
    ES.resolve_pending_triggers()
    assert unit.health == 3

    ES.resolve(Damage(unit, 3))
    ES.resolve_pending_triggers()
    assert unit.health == 0
