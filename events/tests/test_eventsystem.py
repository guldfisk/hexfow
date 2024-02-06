from __future__ import annotations

import dataclasses
import typing as t
from abc import abstractmethod
from typing import Callable

import pytest

from events.eventsystem import (
    EventSystem,
    Event,
    ReplacementEffect,
    TriggerEffect,
    AttributeModifierEffect,
    ModifiableAttribute,
    es,
    E,
    TriggerLoopError,
)


class Dummy:
    damage: int = 0
    position: int = 0
    energy: int = 0

    @classmethod
    def deal_damage(cls, value: int) -> None:
        cls.damage += value

    @classmethod
    def move(cls, value: int) -> None:
        cls.position += value

    @classmethod
    def charge(cls, value: int) -> None:
        cls.energy += value


@pytest.fixture(autouse=True)
def dummy() -> None:
    Dummy.damage = 0
    Dummy.position = 0
    Dummy.energy = 0


@pytest.fixture(autouse=True)
def event_system() -> None:
    EventSystem.init()


@dataclasses.dataclass(kw_only=True)
class HitDummy(Event[int]):
    value: int

    def resolve(self) -> int:
        Dummy.deal_damage(self.value)
        return self.value


@dataclasses.dataclass(kw_only=True)
class MoveDummy(Event[int]):
    distance: int

    def resolve(self) -> int:
        Dummy.move(self.distance)
        return self.distance


@dataclasses.dataclass(kw_only=True)
class ChargeDummy(Event[int]):
    value: int

    def resolve(self) -> int:
        Dummy.charge(self.value)
        return self.value


@dataclasses.dataclass(kw_only=True)
class ResetEnergy(Event[int]):
    def resolve(self) -> int | None:
        return es().resolve_event(ChargeDummy(value=-Dummy.energy))


class DoubleDamage(ReplacementEffect[HitDummy]):
    priority = 0

    def can_replace(self, event: HitDummy) -> bool:
        return True

    def resolve(self, event: HitDummy) -> int | None:
        return es().resolve_event(event.branch(value=event.value * 2))


class AdditionalDamage(ReplacementEffect[HitDummy]):
    priority = 1

    def can_replace(self, event: HitDummy) -> bool:
        return True

    def resolve(self, event: HitDummy) -> int | None:
        return es().resolve_event(event.branch(value=event.value + 1))


class PreventDamage(ReplacementEffect[HitDummy]):
    priority = 2

    def can_replace(self, event: HitDummy) -> bool:
        return True

    def resolve(self, event: HitDummy) -> None:
        ...


class DamageToMove(ReplacementEffect[HitDummy]):
    priority = 3

    def can_replace(self, event: HitDummy) -> bool:
        return True

    def resolve(self, event: HitDummy) -> int | None:
        return es().resolve_event(event.branch(MoveDummy, distance=event.value))


class StaggerTrigger(TriggerEffect[HitDummy]):
    priority = 0

    def should_trigger(self, event: HitDummy) -> t.Callable[[], None] | None:
        return lambda: es().resolve_event(MoveDummy(distance=-event.value))


class DynamoChargeTrigger(TriggerEffect[MoveDummy]):
    priority = 0

    def should_trigger(self, event: MoveDummy) -> t.Callable[[], None] | None:
        return lambda: es().resolve_event(ChargeDummy(value=event.distance))


class DropBatteriesTrigger(TriggerEffect[MoveDummy]):
    priority = 1

    def should_trigger(self, event: MoveDummy) -> t.Callable[[], None] | None:
        if event.distance == 0:
            return None
        return lambda: es().resolve_event(ResetEnergy())


class OverheatTrigger(TriggerEffect[ChargeDummy]):
    priority = 0

    def should_trigger(self, event: ChargeDummy) -> t.Callable[[], None] | None:
        if event.value <= 0:
            return None
        return lambda: es().resolve_event(HitDummy(value=event.value))


class DamageOnDamageTrigger(TriggerEffect[HitDummy]):
    priority = 10

    def should_trigger(self, event: E) -> Callable[[], None] | None:
        return lambda: es().resolve_event(HitDummy(value=1))


class PowerModifier(AttributeModifierEffect[object, int]):
    target_name = "power"

    def __init__(self, target):
        self.target = target

    def should_modify(self, obj: object, value: int) -> bool:
        return self.target == obj

    @abstractmethod
    def modify(self, obj: object, value: int) -> int:
        ...


class DoublePower(PowerModifier):
    priority = 0

    def modify(self, obj: object, value: int) -> int:
        return value * 2


class AddPowerIfEven(PowerModifier):
    priority = 1

    def modify(self, obj: object, value: int) -> int:
        return value + (1 if value % 2 == 0 else 0)


class CapPower(PowerModifier):
    priority = 2

    def __init__(self, target, cap: int):
        super().__init__(target)
        self.cap = cap

    def modify(self, obj: object, value: int) -> int:
        return min(value, self.cap)


@dataclasses.dataclass(eq=False)
class Unit:
    power: int = ModifiableAttribute("power")


def test_single_event():
    assert es().resolve_event(HitDummy(value=1)) == 1
    assert Dummy.damage == 1


def test_two_events():
    for i in range(2):
        es().resolve_event(HitDummy(value=3))
    assert Dummy.damage == 6


def test_replace():
    es().register_effect(DoubleDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 4


def test_deregister_replace():
    es().deregister_effect(es().register_effect(DoubleDamage()))
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2


def test_replace_double_and_add():
    es().register_effect(AdditionalDamage())
    es().register_effect(DoubleDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 5


def test_replace_double_and_add_reversed():
    es().register_effect(DoubleDamage())
    es().register_effect(AdditionalDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 5


def test_prevent_event():
    es().register_effect(PreventDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 0


def test_use_value_from_event():
    damage = es().resolve_event(HitDummy(value=2))
    if damage:
        es().resolve_event(ChargeDummy(value=damage))
    assert Dummy.damage == 2
    assert Dummy.energy == 2


def test_use_value_from_event_with_replacement():
    es().register_effect(DoubleDamage())
    damage = es().resolve_event(HitDummy(value=2))
    if damage:
        es().resolve_event(ChargeDummy(value=damage))
    assert Dummy.damage == 4
    assert Dummy.energy == 4


def test_use_value_from_event_event_prevented():
    es().register_effect(PreventDamage())
    damage = es().resolve_event(HitDummy(value=2))
    if damage:
        es().resolve_event(ChargeDummy(value=damage))
    assert Dummy.damage == 0
    assert Dummy.energy == 0


def test_prevent_event_with_other_replacement():
    es().register_effect(AdditionalDamage())
    es().register_effect(PreventDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 0


def test_replace_swap_event_type():
    es().register_effect(DamageToMove())
    es().resolve_event(HitDummy(value=3))
    assert Dummy.damage == 0
    assert Dummy.position == 3


def test_replace_swap_event_type_with_previous_replacements():
    es().register_effect(DoubleDamage())
    es().register_effect(DamageToMove())
    es().register_effect(DoubleDamage())
    es().resolve_event(HitDummy(value=1))
    assert Dummy.damage == 0
    assert Dummy.position == 4


def test_trigger_effect():
    es().register_effect(StaggerTrigger())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    es().resolve_pending_triggers()
    assert Dummy.position == -2


def test_deregister_effect():
    es().deregister_effect(es().register_effect(StaggerTrigger()))
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2
    es().resolve_pending_triggers()
    assert Dummy.position == 0


def test_multiple_trigger_effects():
    es().register_effect(StaggerTrigger())
    es().register_effect(StaggerTrigger())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    es().resolve_pending_triggers()
    assert Dummy.position == -4


def test_trigger_event_replaced():
    es().register_effect(StaggerTrigger())
    es().register_effect(DoubleDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 4
    assert Dummy.position == 0
    es().resolve_pending_triggers()
    assert Dummy.position == -4


def test_trigger_event_replaced_by_non_triggering_event():
    es().register_effect(StaggerTrigger())
    es().register_effect(PreventDamage())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 0
    es().resolve_pending_triggers()
    assert Dummy.position == 0


def test_trigger_event_replaced_by_new_triggering_event():
    es().register_effect(DynamoChargeTrigger())
    es().register_effect(DamageToMove())
    es().resolve_event(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 2
    assert Dummy.energy == 0
    es().resolve_pending_triggers()
    assert Dummy.energy == 2


def test_trigger_order():
    es().register_effect(DynamoChargeTrigger())
    es().register_effect(DropBatteriesTrigger())
    es().register_effect(DynamoChargeTrigger())
    es().resolve_event(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.energy == 0
    es().resolve_pending_triggers()
    assert Dummy.energy == 0
    assert Dummy.damage == 0


def test_trigger_order_nullified_previous_trigger_still_has_own_triggers():
    es().register_effect(OverheatTrigger())
    es().register_effect(DynamoChargeTrigger())
    es().register_effect(DropBatteriesTrigger())
    es().register_effect(DynamoChargeTrigger())
    es().resolve_event(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.damage == 0
    es().resolve_pending_triggers()
    assert Dummy.energy == 0
    assert Dummy.damage == 4


def test_trigger_loop():
    es().register_effect(DamageOnDamageTrigger())
    es().resolve_event(HitDummy(value=1))
    assert Dummy.damage == 1
    with pytest.raises(TriggerLoopError):
        es().resolve_pending_triggers()


def test_modifiable_attribute():
    unit = Unit(2)
    assert unit.power == 2
    es().register_effect(DoublePower(unit))
    assert unit.power == 4
    assert Unit(3).power == 3


def test_deregister_modifiable_attribute():
    units = [Unit(v) for v in (1, 2)]
    effects = [es().register_effect(DoublePower(unit)) for unit in units]
    es().deregister_effect(effects[0])
    assert units[0].power == 1
    assert units[1].power == 4


def test_set_modifiable_attribute():
    unit = Unit(2)
    assert unit.power == 2
    es().register_effect(DoublePower(unit))
    assert unit.power == 4
    unit.power = 3
    assert unit.power == 6


def test_attribute_modification_order():
    units = [Unit(2) for _ in range(3)]

    es().register_effect(DoublePower(units[0]))
    es().register_effect(DoublePower(units[0]))

    dp = es().register_effect(DoublePower(units[1]))
    es().register_effect(AddPowerIfEven(units[1]))

    es().register_effect(DoublePower(units[2]))
    cap = es().register_effect(CapPower(units[2], 3))
    es().register_effect(DoublePower(units[2]))

    assert units[0].power == 8

    assert units[1].power == 5
    units[1].power = 1
    assert units[1].power == 3
    es().deregister_effect(dp)
    assert units[1].power == 1

    assert units[2].power == 3
    es().deregister_effect(cap)
    assert units[2].power == 8
