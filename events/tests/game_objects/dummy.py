import dataclasses

from events.eventsystem import EventSystem, Event, ReplacementEffect, E, TriggerEffect


class Dummy:
    damage: int = 0
    position: int = 0
    energy: int = 0
    armor: int = 0

    @classmethod
    def reset(cls) -> None:
        cls.damage = 0
        cls.position = 0
        cls.energy = 0
        cls.armor = 0

    @classmethod
    def deal_damage(cls, value: int) -> None:
        cls.damage += value

    @classmethod
    def move(cls, value: int) -> None:
        cls.position += value

    @classmethod
    def charge(cls, value: int) -> None:
        cls.energy += value


@dataclasses.dataclass
class DummyLossHealth(Event[int]):
    value: int

    def is_valid(self) -> bool:
        return self.value > 0

    def resolve(self, es: EventSystem) -> int:
        Dummy.deal_damage(self.value)
        return self.value


@dataclasses.dataclass
class DamageDummy(Event[int]):
    value: int

    def is_valid(self) -> bool:
        return self.value > 0

    def resolve(self, es: EventSystem) -> int:
        damage_value = max(self.value - Dummy.armor, 0)
        es.resolve(DummyLossHealth(damage_value))
        return damage_value


@dataclasses.dataclass
class HitDummy(Event[None]):
    value: int

    def is_valid(self) -> bool:
        return self.value > 0

    def resolve(self, es: EventSystem) -> None:
        es.resolve(DamageDummy(self.value))


@dataclasses.dataclass
class MoveDummy(Event[int]):
    distance: int

    def is_valid(self) -> bool:
        return self.distance != 0

    def resolve(self, es: EventSystem) -> int:
        Dummy.move(self.distance)
        return self.distance


@dataclasses.dataclass
class ChargeDummy(Event[int]):
    value: int

    def is_valid(self) -> bool:
        return self.value > 0

    def resolve(self, es: EventSystem) -> int:
        Dummy.charge(self.value)
        return self.value


class ResetEnergy(Event[None]):
    def resolve(self, es: EventSystem) -> None:
        Dummy.energy = 0


class DoubleDamage(ReplacementEffect[DamageDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: E) -> None:
        es.resolve(event.branch(value=event.value * 2))


class AdditionalDamage(ReplacementEffect[DamageDummy]):
    priority = 1

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve(event.branch(value=event.value + 1))


class PreventDamage(ReplacementEffect[DamageDummy]):
    priority = 2

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        return None


class DamageToMove(ReplacementEffect[DamageDummy]):
    priority = 3

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve(MoveDummy(distance=event.value))


class MoveToDamage(ReplacementEffect[MoveDummy]):
    priority = 4

    def resolve(self, es: EventSystem, event: MoveDummy) -> None:
        es.resolve(DamageDummy(value=event.distance))


class DamageAlsoMoves(ReplacementEffect[DamageDummy]):
    priority = -1

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve(MoveDummy(distance=event.value))
        es.resolve(event)


class StaggerTrigger(TriggerEffect[DamageDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve(MoveDummy(-event.value))


class DynamoChargeTrigger(TriggerEffect[MoveDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: MoveDummy) -> None:
        es.resolve(ChargeDummy(abs(event.distance)))


class DropBatteriesTrigger(TriggerEffect[MoveDummy]):
    priority = 1

    def resolve(self, es: EventSystem, event: MoveDummy) -> None:
        es.resolve(ResetEnergy())


class OverheatTrigger(TriggerEffect[ChargeDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: ChargeDummy) -> None:
        es.resolve(DamageDummy(event.value))


class HitOnDamageTrigger(TriggerEffect[DamageDummy]):
    priority = 10

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve(HitDummy(1))
