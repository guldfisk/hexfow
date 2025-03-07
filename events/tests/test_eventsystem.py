from __future__ import annotations

import dataclasses

import pytest

from events.eventsystem import (
    EventSystem,
    Event,
    ReplacementEffect,
    E,
    V,
    TriggerEffect,
    TriggerLoopError, ModifiableAttribute,
)


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


@pytest.fixture(autouse=True)
def dummy() -> None:
    Dummy.reset()
    # Dummy.damage = 0
    # Dummy.position = 0
    # Dummy.energy = 0


# @pytest.fixture(autouse=True)
# def event_system() -> None:
#     EventSystem.init()


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
        es.resolve_event(DummyLossHealth(damage_value))
        return damage_value


@dataclasses.dataclass
class HitDummy(Event[None]):
    value: int

    def is_valid(self) -> bool:
        return self.value > 0

    def resolve(self, es: EventSystem) -> None:
        es.resolve_event(DamageDummy(self.value))


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
        es.resolve_event(event.branch(value=event.value * 2))


class AdditionalDamage(ReplacementEffect[DamageDummy]):
    priority = 1

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve_event(event.branch(value=event.value + 1))


class PreventDamage(ReplacementEffect[DamageDummy]):
    priority = 2

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        return None


class DamageToMove(ReplacementEffect[DamageDummy]):
    priority = 3

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve_event(MoveDummy(distance=event.value))


class MoveToDamage(ReplacementEffect[MoveDummy]):
    priority = 4

    def resolve(self, es: EventSystem, event: MoveDummy) -> None:
        es.resolve_event(DamageDummy(value=event.distance))


class DamageAlsoMoves(ReplacementEffect[DamageDummy]):
    priority = -1

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve_event(MoveDummy(distance=event.value))
        es.resolve_event(event)


class StaggerTrigger(TriggerEffect[DamageDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve_event(MoveDummy(-event.value))


class DynamoChargeTrigger(TriggerEffect[MoveDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: MoveDummy) -> None:
        es.resolve_event(ChargeDummy(abs(event.distance)))


class DropBatteriesTrigger(TriggerEffect[MoveDummy]):
    priority = 1

    def resolve(self, es: EventSystem, event: MoveDummy) -> None:
        es.resolve_event(ResetEnergy())


class OverheatTrigger(TriggerEffect[ChargeDummy]):
    priority = 0

    def resolve(self, es: EventSystem, event: ChargeDummy) -> None:
        es.resolve_event(DamageDummy(event.value))


class HitOnDamageTrigger(TriggerEffect[DamageDummy]):
    priority = 10

    def resolve(self, es: EventSystem, event: DamageDummy) -> None:
        es.resolve_event(HitDummy(1))


#
#
# class PowerModifier(AttributeModifierEffect[object, int]):
#     target_name = "power"
#
#     def __init__(self, target):
#         self.target = target
#
#     def should_modify(self, obj: object, value: int) -> bool:
#         return self.target == obj
#
#     @abstractmethod
#     def modify(self, obj: object, value: int) -> int:
#         ...
#
#
# class DoublePower(PowerModifier):
#     priority = 0
#
#     def modify(self, obj: object, value: int) -> int:
#         return value * 2
#
#
# class AddPowerIfEven(PowerModifier):
#     priority = 1
#
#     def modify(self, obj: object, value: int) -> int:
#         return value + (1 if value % 2 == 0 else 0)
#
#
# class CapPower(PowerModifier):
#     priority = 2
#
#     def __init__(self, target, cap: int):
#         super().__init__(target)
#         self.cap = cap
#
#     def modify(self, obj: object, value: int) -> int:
#         return min(value, self.cap)
#
#
@dataclasses.dataclass(eq=False)
class Unit:
    power: int = ModifiableAttribute("power")


@pytest.fixture
def es() -> EventSystem:
    return EventSystem()


def _check_history(es: EventSystem, target: list[Event]):
    assert [
        type(e)(
            **{
                f.name: getattr(e, f.name)
                for f in dataclasses.fields(e)
                if f.name not in ("parent", "children")
            }
        )
        for e in es.history
    ] == target


def test_single_event(es: EventSystem):
    assert (
        sum(
            e.value
            for e in es.resolve_event(DummyLossHealth(1)).iter_type(DummyLossHealth)
        )
        == 1
    )
    assert Dummy.damage == 1
    # assert es.history == [DummyLossHealth(1, result=1)]
    _check_history(es, [DummyLossHealth(1, result=1)])


def test_event_spawning_other_event(es: EventSystem):
    resolution = es.resolve_event(DamageDummy(1))
    for event_type in (DamageDummy, DummyLossHealth):
        assert sum(e.value for e in resolution.iter_type(event_type)) == 1
    assert Dummy.damage == 1
    print(es.history)
    # assert es.history == [DummyLossHealth(1, result=1), DamageDummy(1, result=1)]
    _check_history(es, [DummyLossHealth(1, result=1), DamageDummy(1, result=1)])


def test_two_events(es: EventSystem):
    for i in range(2):
        es.resolve_event(DamageDummy(value=3))
    assert Dummy.damage == 6


def test_invalid_event(es: EventSystem):
    assert not list(es.resolve_event(DamageDummy(value=0)).iter_type(DamageDummy))
    assert Dummy.damage == 0


def test_replace(es: EventSystem):
    es.register_effect(DoubleDamage())
    assert (
        sum(
            e.value
            for e in es.resolve_event(DamageDummy(value=2)).iter_type(DamageDummy)
        )
        == 4
    )
    assert Dummy.damage == 4


def test_multiple_same_replacement_effect(es: EventSystem):
    for _ in range(3):
        es.register_effect(DoubleDamage())

    assert es.resolve_event(DamageDummy(value=3))

    assert Dummy.damage == 24


def test_multiple_replaced_events(es: EventSystem):
    es.register_effect(DoubleDamage())
    for _ in range(2):
        es.resolve_event(DamageDummy(value=2))

    assert Dummy.damage == 8


def test_deregister_replace(es: EventSystem):
    es.deregister_effect(es.register_effect(DoubleDamage()))
    es.resolve_event(DamageDummy(value=2))
    assert Dummy.damage == 2


def test_prevent_event(es: EventSystem):
    es.register_effect(PreventDamage())
    assert not list(es.resolve_event(DamageDummy(value=2)).iter_type(DamageDummy))
    assert Dummy.damage == 0


def test_replace_swap_event_type(es: EventSystem):
    es.register_effect(DamageToMove())
    resolution = es.resolve_event(DamageDummy(value=3))
    print(resolution)
    assert not list(resolution.iter_type(DamageDummy))
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 3
    assert Dummy.damage == 0
    assert Dummy.position == 3
    assert es.history == [MoveDummy(distance=3, result=3)]


def test_double_swap(es: EventSystem):
    es.register_effect(MoveToDamage())
    es.register_effect(DamageToMove())
    resolution = es.resolve_event(DamageDummy(3))
    assert not list(resolution.iter_type(MoveDummy))
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 3
    assert Dummy.damage == 3
    assert Dummy.position == 0
    assert es.history == [DummyLossHealth(3, result=3), DamageDummy(3, result=3)]


def test_event_affected_by_multiple_different_replacements(es: EventSystem):
    es.register_effect(AdditionalDamage())
    es.register_effect(DoubleDamage())
    es.resolve_event(DamageDummy(2))
    assert Dummy.damage == 5


def test_replacement_spawns_multiple_events(es: EventSystem):
    es.register_effect(DamageAlsoMoves())
    resolution = es.resolve_event(DamageDummy(1))
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 1
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 1
    assert Dummy.damage == 1
    assert Dummy.position == 1
    assert es.history == [
        MoveDummy(1, result=1),
        DummyLossHealth(1, result=1),
        DamageDummy(1, result=1),
    ]


def test_replacement_spawns_multiple_events_multiple_times(es: EventSystem):
    for _ in range(2):
        es.register_effect(DamageAlsoMoves())
    resolution = es.resolve_event(DamageDummy(1))
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 2
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 1
    assert Dummy.damage == 1
    assert Dummy.position == 2
    assert es.history == [
        MoveDummy(1, result=1),
        MoveDummy(1, result=1),
        DummyLossHealth(1, result=1),
        DamageDummy(1, result=1),
    ]


def test_event_using_result_of_other_event(es: EventSystem):
    @dataclasses.dataclass
    class StaggeringAttack(Event[None]):
        strength: int

        def resolve(self, es: EventSystem) -> None:
            es.resolve_event(
                MoveDummy(
                    sum(
                        e.result
                        for e in es.resolve_event(HitDummy(self.strength)).iter_type(
                            DamageDummy
                        )
                    )
                )
            )

    Dummy.armor = 1

    es.resolve_event(StaggeringAttack(2))

    assert Dummy.damage == 1
    assert Dummy.position == 1


def test_event_conditional_result_of_other_event(es: EventSystem):
    @dataclasses.dataclass
    class BloodThirstyAttack(Event[None]):
        strength: int

        def resolve(self, es: EventSystem) -> None:
            if es.resolve_event(HitDummy(value=self.strength)).has_type(
                DummyLossHealth
            ):
                es.resolve_event(HitDummy(value=2))

    Dummy.armor = 1

    es.resolve_event(BloodThirstyAttack(3))
    assert Dummy.damage == 3

    es.resolve_event(BloodThirstyAttack(1))
    assert Dummy.damage == 3

    # class HitAlsoMoves(ReplacementEffect[HitDummy]):
    #     priority = -1
    #
    #     def resolve(self, es: EventSystem, event: HitDummy) -> None:
    #         es.resolve_event(MoveDummy(distance=event.value))
    #         es.resolve_event(event)


def test_event_searches_history(es: EventSystem):
    class EchoAttack(Event[None]):

        def resolve(self, es: EventSystem) -> None:
            if previous_hit := es.last_event_of_type(HitDummy):
                es.resolve_event(HitDummy(previous_hit.value))

    es.resolve_event(EchoAttack())
    assert es.history == [EchoAttack()]
    assert Dummy.damage == 0

    es.resolve_event(HitDummy(1))
    assert Dummy.damage == 1

    es.resolve_event(EchoAttack())
    assert Dummy.damage == 2

    es.resolve_event(HitDummy(2))
    assert Dummy.damage == 4

    es.resolve_event(EchoAttack())
    assert Dummy.damage == 6


def test_event_searches_historic_event_children(es: EventSystem):
    class EchoPainAttack(Event[None]):

        def resolve(self, es: EventSystem) -> None:
            if previous_hit := es.last_event_of_type(HitDummy):
                es.resolve_event(
                    HitDummy(
                        sum(e.value for e in previous_hit.iter_type(DummyLossHealth))
                    )
                )

    Dummy.armor = 1

    es.resolve_event(EchoPainAttack())
    assert es.history == [EchoPainAttack()]
    assert Dummy.damage == 0

    es.resolve_event(HitDummy(3))
    assert Dummy.damage == 2

    es.resolve_event(EchoPainAttack())
    assert Dummy.damage == 3

    es.resolve_event(EchoPainAttack())
    assert Dummy.damage == 3

    es.register_effect(DamageAlsoMoves())
    es.register_effect(MoveToDamage())

    Dummy.damage = 0

    es.resolve_event(HitDummy(3))
    assert Dummy.damage == 4

    es.resolve_event(EchoPainAttack())
    assert Dummy.damage == 10


def test_trigger_effect(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -2
    assert not es.has_pending_triggers()


def test_multiple_trigger_effects(es: EventSystem):
    for _ in range(2):
        es.register_effect(StaggerTrigger())
    es.resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -4
    assert not es.has_pending_triggers()


def test_trigger_on_replaced_effect(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.register_effect(DoubleDamage())
    es.resolve_event(HitDummy(value=2))
    assert Dummy.damage == 4
    assert Dummy.position == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -4
    assert not es.has_pending_triggers()


def test_chained_triggers(es: EventSystem):
    es.register_effect(DynamoChargeTrigger())
    es.register_effect(StaggerTrigger())
    es.resolve_event(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    assert Dummy.energy == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -2
    assert Dummy.energy == 2
    assert not es.has_pending_triggers()


def test_trigger_event_prevented(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.register_effect(PreventDamage())
    es.resolve_event(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 0
    assert not es.has_pending_triggers()


def test_trigger_event_replaced_by_non_triggering_event(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.register_effect(DamageToMove())
    es.resolve_event(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 2
    assert not es.has_pending_triggers()


def test_trigger_order(es: EventSystem):
    es.register_effect(DynamoChargeTrigger())
    es.register_effect(DropBatteriesTrigger())
    es.register_effect(DynamoChargeTrigger())
    es.resolve_event(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.energy == 0
    es.resolve_pending_triggers()
    assert Dummy.energy == 0


def test_trigger_order_nullified_previous_trigger_still_has_own_triggers(
    es: EventSystem,
):
    es.register_effect(OverheatTrigger())
    es.register_effect(DynamoChargeTrigger())
    es.register_effect(DropBatteriesTrigger())
    es.register_effect(DynamoChargeTrigger())
    es.resolve_event(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.damage == 0
    es.resolve_pending_triggers()
    assert Dummy.energy == 0
    assert Dummy.damage == 4


def test_trigger_loop(es: EventSystem):
    es.register_effect(HitOnDamageTrigger())
    es.resolve_event(HitDummy(value=1))
    assert Dummy.damage == 1
    with pytest.raises(TriggerLoopError):
        es.resolve_pending_triggers()


#
# def test_modifiable_attribute():
#     unit = Unit(2)
#     assert unit.power == 2
#     es.register_effect(DoublePower(unit))
#     assert unit.power == 4
#     assert Unit(3).power == 3
#
#
# def test_modifiable_attribute_get_base():
#     unit = Unit(2)
#     es.register_effect(DoublePower(unit))
#     assert unit.power == 4
#     assert Unit.power.get(unit) == 4
#     assert Unit.power.get_base(unit) == 2
#
#
# def test_deregister_modifiable_attribute():
#     units = [Unit(v) for v in (1, 2)]
#     effects = [es.register_effect(DoublePower(unit)) for unit in units]
#     es.deregister_effect(effects[0])
#     assert units[0].power == 1
#     assert units[1].power == 4
#
#
# def test_set_modifiable_attribute():
#     unit = Unit(2)
#     assert unit.power == 2
#     es.register_effect(DoublePower(unit))
#     assert unit.power == 4
#     unit.power = 3
#     assert unit.power == 6
#
#
# def test_attribute_modification_order():
#     units = [Unit(2) for _ in range(3)]
#
#     es.register_effect(DoublePower(units[0]))
#     es.register_effect(DoublePower(units[0]))
#
#     dp = es.register_effect(DoublePower(units[1]))
#     es.register_effect(AddPowerIfEven(units[1]))
#
#     es.register_effect(DoublePower(units[2]))
#     cap = es.register_effect(CapPower(units[2], 3))
#     es.register_effect(DoublePower(units[2]))
#
#     assert units[0].power == 8
#
#     assert units[1].power == 5
#     units[1].power = 1
#     assert units[1].power == 3
#     es.deregister_effect(dp)
#     assert units[1].power == 1
#
#     assert units[2].power == 3
#     es.deregister_effect(cap)
#     assert units[2].power == 8
