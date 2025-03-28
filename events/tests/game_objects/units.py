from __future__ import annotations

import dataclasses
from abc import ABC
from typing import ClassVar

from debug_utils import dp
from events.eventsystem import (
    Event,
    V,
    ModifiableAttribute,
    Modifiable,
    StateModifierEffect,
    modifiable,
)


class Unit(Modifiable):
    power: ModifiableAttribute[None, int]
    toughness: ModifiableAttribute[None, int]

    def __init__(
        self,
        power: int = 1,
        toughness: int = 1,
    ):
        self.power.set(power)
        self.toughness.set(toughness)
        self.position = 0
        self.health = 10

    @modifiable
    def can_be_attacked_by(self, unit: Unit) -> bool:
        return True

    @modifiable
    def can_merge_with(self, unit: Unit) -> bool:
        return False


@dataclasses.dataclass
class Move(Event[None]):
    unit: Unit
    amount: int

    def resolve(self) -> None:
        self.unit.position += self.amount


@dataclasses.dataclass
class Damage(Event[None]):
    unit: Unit
    amount: int

    def resolve(self) -> None:
        self.unit.health -= self.amount


class UnitModifier(StateModifierEffect[Unit, None, V], ABC):
    def __init__(self, target_unit: Unit):
        self.target_unit = target_unit

    def should_modify(self, obj: Unit, request: None, value: V) -> V:
        return self.target_unit == obj


class PowerModifier(UnitModifier[int], ABC):
    target = Unit.power


class DoublePower(PowerModifier):
    priority = 0

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value * 2


class AddPowerIfEven(PowerModifier):
    priority = 1

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (1 if value % 2 == 0 else 0)


class AddToughnessToPower(PowerModifier):
    priority = 2

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + obj.toughness.get(None)


class CapPower(PowerModifier):
    priority = 3

    def __init__(self, target, cap: int):
        super().__init__(target)
        self.cap = cap

    def modify(self, obj: object, request: None, value: int) -> int:
        return min(value, self.cap)


class ToughnessModifier(UnitModifier[int], ABC):
    target = Unit.toughness


class AddPowerToToughness(ToughnessModifier):
    priority = 1

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + obj.power.get(None)


class ToughnessAtLeastPower(ToughnessModifier):
    priority = 2

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return max(value, obj.power.get(None))


@dataclasses.dataclass(eq=False)
class AttackShield(StateModifierEffect[Unit, Unit, bool]):
    priority: ClassVar[int] = 3
    target: ClassVar[object] = Unit.can_be_attacked_by

    shield_on: Unit
    shield_against: Unit

    def should_modify(self, obj: Unit, request: Unit, value: bool) -> V:
        return obj == self.shield_on and request == self.shield_against

    def modify(self, obj: Unit, request: Unit, value: bool) -> V:
        return False


@dataclasses.dataclass(eq=False)
class AttackShieldPenetrator(StateModifierEffect[Unit, Unit, bool]):
    priority: ClassVar[int] = 4
    target: ClassVar[object] = Unit.can_be_attacked_by

    unit: Unit

    def should_modify(self, obj: Unit, request: Unit, value: bool) -> V:
        return request == self.unit

    def modify(self, obj: Unit, request: Unit, value: bool) -> V:
        return True
