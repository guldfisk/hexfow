import dataclasses
from abc import ABC

import pytest

from events.eventsystem import (
    TriggerLoopError,
    Event,
    ReplacementEffect,
    TriggerEffect,
    E,
    ES,
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


def test_trigger_effect():
    ES.register_effects(StaggerTrigger())
    ES.resolve(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    ES.resolve_pending_triggers()
    assert Dummy.position == -2
    assert not ES.has_pending_triggers()


def test_multiple_trigger_effects():
    for _ in range(2):
        ES.register_effects(StaggerTrigger())
    ES.resolve(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    ES.resolve_pending_triggers()
    assert Dummy.position == -4
    assert not ES.has_pending_triggers()


def test_trigger_on_replaced_effect():
    ES.register_effects(StaggerTrigger())
    ES.register_effects(DoubleDamage())
    ES.resolve(HitDummy(value=2))
    assert Dummy.damage == 4
    assert Dummy.position == 0
    ES.resolve_pending_triggers()
    assert Dummy.position == -4
    assert not ES.has_pending_triggers()


def test_chained_triggers():
    ES.register_effects(DynamoChargeTrigger())
    ES.register_effects(StaggerTrigger())
    ES.resolve(HitDummy(value=2))
    assert Dummy.damage == 2
    assert Dummy.position == 0
    assert Dummy.energy == 0
    ES.resolve_pending_triggers()
    assert Dummy.position == -2
    assert Dummy.energy == 2
    assert not ES.has_pending_triggers()


def test_trigger_event_prevented():
    ES.register_effects(StaggerTrigger())
    ES.register_effects(PreventDamage())
    ES.resolve(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 0
    assert not ES.has_pending_triggers()


def test_trigger_event_replaced_by_non_triggering_event():
    ES.register_effects(StaggerTrigger())
    ES.register_effects(DamageToMove())
    ES.resolve(HitDummy(value=2))
    assert Dummy.damage == 0
    assert Dummy.position == 2
    assert not ES.has_pending_triggers()


def test_trigger_order():
    ES.register_effects(DynamoChargeTrigger())
    ES.register_effects(DropBatteriesTrigger())
    ES.register_effects(DynamoChargeTrigger())
    ES.resolve(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.energy == 0
    ES.resolve_pending_triggers()
    assert Dummy.energy == 0


def test_trigger_order_nullified_previous_trigger_still_has_own_triggers():
    ES.register_effects(OverheatTrigger())
    ES.register_effects(DynamoChargeTrigger())
    ES.register_effects(DropBatteriesTrigger())
    ES.register_effects(DynamoChargeTrigger())
    ES.resolve(MoveDummy(distance=2))
    assert Dummy.position == 2
    assert Dummy.damage == 0
    ES.resolve_pending_triggers()
    assert Dummy.energy == 0
    assert Dummy.damage == 4


def test_trigger_loop():
    ES.register_effects(HitOnDamageTrigger())
    ES.resolve(HitDummy(value=1))
    assert Dummy.damage == 1
    with pytest.raises(TriggerLoopError):
        ES.resolve_pending_triggers()


def test_trigger_abc():
    @dataclasses.dataclass(eq=False)
    class UnitTrigger(TriggerEffect[E], ABC):
        unit: Unit

    class MoveOnDamageUnitTrigger(UnitTrigger[Damage]):
        priority = 1

        def resolve(self, event: Damage) -> None:
            ES.resolve(event.branch(Move))

    unit = Unit()
    ES.register_effects(MoveOnDamageUnitTrigger(unit))
    ES.resolve(Damage(unit, 1))

    assert unit.health == 9
    ES.resolve_pending_triggers()
    assert unit.position == 1


def test_delayed_trigger():
    class RepeatDamage(TriggerEffect[Damage]):
        priority = 1

        def should_deregister(self, event: Damage) -> bool:
            return True

        def resolve(self, event: Damage) -> None:
            ES.resolve(event.branch())

    unit = Unit()
    ES.register_effects(RepeatDamage())
    ES.resolve(Damage(unit, 1))
    ES.resolve_pending_triggers()
    assert unit.health == 8


def test_trigger_within_replacement():
    units = [Unit() for _ in range(2)]

    @dataclasses.dataclass
    class MovePhase(Event[None]):
        speed: int

        def resolve(
            self,
        ) -> None:
            for unit in units:
                ES.resolve(Move(unit, self.speed))
            ES.resolve_pending_triggers()

    class Speedy(ReplacementEffect[MovePhase]):
        priority = 1

        def resolve(self, event: MovePhase) -> None:
            ES.resolve(event.branch(speed=event.speed * 2))

    class MovePhaseOnMove(TriggerEffect[Move]):
        priority = 1

        def should_deregister(self, event: Move) -> bool:
            return True

        def resolve(self, event: Move) -> None:
            ES.resolve(MovePhase(1))

    for _ in range(2):
        ES.register_effects(Speedy())
    ES.register_effects(MovePhaseOnMove())

    ES.resolve(MovePhase(2))

    # Speedy replacement is applied to both movement phases, even though
    # the second it resolved within the first, since resolving a trigger
    # starts a new replacement context.
    for unit in units:
        assert unit.position == 2 * 2 * 2 + 1 * 2 * 2
