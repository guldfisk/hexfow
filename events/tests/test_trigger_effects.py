import dataclasses
from abc import ABC

import pytest

from events.eventsystem import (
    EventSystem,
    TriggerLoopError,
    Event,
    ReplacementEffect,
    TriggerEffect,
    E,
)
from events.tests.game_objects.dummy import (
    StaggerTrigger,
    HitDummy,
    Dummy,
    DoubleDamage,
    DynamoChargeTrigger,
    PreventDamage,
    DamageToMove,
    DropBatteriesTrigger,
    MoveDummy,
    OverheatTrigger,
    HitOnDamageTrigger,
)
from events.tests.game_objects.units import Unit, Damage, Move


def test_trigger_effect(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.resolve(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -2
    assert not es.has_pending_triggers()


def test_multiple_trigger_effects(es: EventSystem):
    for _ in range(2):
        es.register_effect(StaggerTrigger())
    es.resolve(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -4
    assert not es.has_pending_triggers()


def test_trigger_on_replaced_effect(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.register_effect(DoubleDamage())
    es.resolve(HitDummy(value=2))
    assert Dummy.damage == 4
    assert Dummy.position == 0
    es.resolve_pending_triggers()
    assert Dummy.position == -4
    assert not es.has_pending_triggers()


def test_chained_triggers(es: EventSystem):
    es.register_effect(DynamoChargeTrigger())
    es.register_effect(StaggerTrigger())
    es.resolve(HitDummy(value=2))
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
    es.resolve(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 0
    assert not es.has_pending_triggers()


def test_trigger_event_replaced_by_non_triggering_event(es: EventSystem):
    es.register_effect(StaggerTrigger())
    es.register_effect(DamageToMove())
    es.resolve(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 2
    assert not es.has_pending_triggers()


def test_trigger_order(es: EventSystem):
    es.register_effect(DynamoChargeTrigger())
    es.register_effect(DropBatteriesTrigger())
    es.register_effect(DynamoChargeTrigger())
    es.resolve(MoveDummy(distance=2))
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
    es.resolve(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.damage == 0
    es.resolve_pending_triggers()
    assert Dummy.energy == 0
    assert Dummy.damage == 4


def test_trigger_loop(es: EventSystem):
    es.register_effect(HitOnDamageTrigger())
    es.resolve(HitDummy(value=1))
    assert Dummy.damage == 1
    with pytest.raises(TriggerLoopError):
        es.resolve_pending_triggers()


def test_trigger_abc(es: EventSystem):
    @dataclasses.dataclass
    class UnitTrigger(TriggerEffect[E], ABC):
        unit: Unit

    class MoveOnDamageUnitTrigger(UnitTrigger[Damage]):
        priority = 1

        def resolve(self, es: EventSystem, event: Damage) -> None:
            es.resolve(event.branch(Move))

    unit = Unit()
    es.register_effect(MoveOnDamageUnitTrigger(unit))
    es.resolve(Damage(unit, 1))

    assert unit.health == 9
    es.resolve_pending_triggers()
    assert unit.position == 1


def test_delayed_trigger(es: EventSystem):
    class RepeatDamage(TriggerEffect[Damage]):
        priority = 1

        def should_deregister(self, es: EventSystem, event: Damage) -> bool:
            return True

        def resolve(self, es: EventSystem, event: Damage) -> None:
            es.resolve(event.branch())

    unit = Unit()
    es.register_effect(RepeatDamage())
    es.resolve(Damage(unit, 1))
    es.resolve_pending_triggers()
    assert unit.health == 8


def test_trigger_within_replacement(es: EventSystem):
    units = [Unit() for _ in range(2)]

    @dataclasses.dataclass
    class MovePhase(Event[None]):
        speed: int

        def resolve(self, es: EventSystem) -> None:
            for unit in units:
                es.resolve(Move(unit, self.speed))
            es.resolve_pending_triggers()

    class Speedy(ReplacementEffect[MovePhase]):
        priority = 1

        def resolve(self, es: EventSystem, event: MovePhase) -> None:
            es.resolve(event.branch(speed=event.speed * 2))

    class MovePhaseOnMove(TriggerEffect[Move]):
        priority = 1

        def should_deregister(self, es: EventSystem, event: Move) -> bool:
            return True

        def resolve(self, es: EventSystem, event: Move) -> None:
            es.resolve(MovePhase(1))

    for _ in range(2):
        es.register_effect(Speedy())
    es.register_effect(MovePhaseOnMove())

    es.resolve(MovePhase(2))

    # Speedy replacement is applied to both movement phases, even though
    # the second it resolved within the first, since resolving a trigger
    # starts a new replacement context.
    for unit in units:
        assert unit.position == 2 * 2 * 2 + 1 * 2 * 2
