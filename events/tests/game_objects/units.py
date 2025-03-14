import dataclasses
from abc import ABC

from debug_utils import dp
from events.eventsystem import (
    EventSystem,
    Event,
    V,
    ModifiableAttribute,
    AttributeModifierEffect,
    WithModifiableAttributes,
)


class Unit(WithModifiableAttributes):
    power: ModifiableAttribute[int]
    toughness: ModifiableAttribute[int]

    def __init__(
        self,
        power: int = 1,
        toughness: int = 1,
    ):
        self.power.set(power)
        self.toughness.set(toughness)
        self.position = 0
        self.health = 10


@dataclasses.dataclass
class Move(Event[None]):
    unit: Unit
    amount: int

    def resolve(self, es: EventSystem) -> None:
        self.unit.position += self.amount


@dataclasses.dataclass
class Damage(Event[None]):
    unit: Unit
    amount: int

    def resolve(self, es: EventSystem) -> None:
        self.unit.health -= self.amount


class UnitModifier(AttributeModifierEffect[Unit, V], ABC):
    def __init__(self, target_unit: Unit):
        self.target_unit = target_unit

    def should_modify(self, obj: Unit, value: V, es: EventSystem) -> bool:
        return self.target_unit == obj


class PowerModifier(UnitModifier[int], ABC):
    # TODO modifiable attribute?
    target = Unit.power


dp(PowerModifier.target)


# assert PowerModifier.target is None


class DoublePower(PowerModifier):
    priority = 0

    def modify(self, obj: Unit, value: int, es: EventSystem) -> int:
        return value * 2


class AddPowerIfEven(PowerModifier):
    priority = 1

    def modify(self, obj: Unit, value: int, es: EventSystem) -> int:
        return value + (1 if value % 2 == 0 else 0)


class AddToughnessToPower(PowerModifier):
    priority = 2

    def modify(self, obj: Unit, value: int, es: EventSystem) -> int:
        return value + obj.toughness.get(es)


class CapPower(PowerModifier):
    priority = 3

    def __init__(self, target, cap: int):
        super().__init__(target)
        self.cap = cap

    def modify(self, obj: object, value: int, es: EventSystem) -> int:
        return min(value, self.cap)


class ToughnessModifier(UnitModifier[int], ABC):
    target = Unit.toughness


class AddPowerToToughness(ToughnessModifier):
    priority = 1

    def modify(self, obj: Unit, value: int, es: EventSystem) -> int:
        return value + obj.power.get(es)


class ToughnessAtLeastPower(ToughnessModifier):
    priority = 2

    def modify(self, obj: Unit, value: int, es: EventSystem) -> int:
        return max(value, obj.power.get(es))
