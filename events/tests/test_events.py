import dataclasses

from events.eventsystem import EventSystem, Event
from events.tests.game_objects.dummy import (
    DamageDummy,
    DummyLossHealth,
    Dummy,
    MoveDummy,
    HitDummy,
)
from events.tests.utils import check_history


def test_single_event(es: EventSystem):
    assert (
        sum(
            e.value
            for e in es.resolve(DummyLossHealth(1)).iter_type(DummyLossHealth)
        )
        == 1
    )
    assert Dummy.damage == 1
    check_history(es, [DummyLossHealth(1, result=1)])


def test_event_spawning_other_event(es: EventSystem):
    resolution = es.resolve(DamageDummy(1))
    for event_type in (DamageDummy, DummyLossHealth):
        assert sum(e.value for e in resolution.iter_type(event_type)) == 1
    assert Dummy.damage == 1
    check_history(es, [DummyLossHealth(1, result=1), DamageDummy(1, result=1)])


def test_two_events(es: EventSystem):
    for i in range(2):
        es.resolve(DamageDummy(value=3))
    assert Dummy.damage == 6


def test_invalid_event(es: EventSystem):
    assert not list(es.resolve(DamageDummy(value=0)).iter_type(DamageDummy))
    assert Dummy.damage == 0


def test_event_using_result_of_other_event(es: EventSystem):
    @dataclasses.dataclass
    class StaggeringAttack(Event[None]):
        strength: int

        def resolve(self, es: EventSystem) -> None:
            es.resolve(
                MoveDummy(
                    sum(
                        e.result
                        for e in es.resolve(HitDummy(self.strength)).iter_type(
                            DamageDummy
                        )
                    )
                )
            )

    Dummy.armor = 1

    es.resolve(StaggeringAttack(2))

    assert Dummy.damage == 1
    assert Dummy.position == 1


def test_event_conditional_result_of_other_event(es: EventSystem):
    @dataclasses.dataclass
    class BloodThirstyAttack(Event[None]):
        strength: int

        def resolve(self, es: EventSystem) -> None:
            if es.resolve(HitDummy(value=self.strength)).has_type(
                DummyLossHealth
            ):
                es.resolve(HitDummy(value=2))

    Dummy.armor = 1

    es.resolve(BloodThirstyAttack(3))
    assert Dummy.damage == 3

    es.resolve(BloodThirstyAttack(1))
    assert Dummy.damage == 3
