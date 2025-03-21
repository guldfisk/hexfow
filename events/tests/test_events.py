import dataclasses

from events.eventsystem import Event, ES
from events.tests.game_objects.dummy import (
    DamageDummy,
    DummyLossHealth,
    Dummy,
    MoveDummy,
    HitDummy,
)
from events.tests.utils import check_history


def test_single_event():
    assert (
        sum(
            e.value for e in ES.resolve(DummyLossHealth(1)).iter_type(DummyLossHealth)
        )
        == 1
    )
    assert Dummy.damage == 1
    check_history(ES, [DummyLossHealth(1, result=1)])


def test_event_spawning_other_event():
    resolution = ES.resolve(DamageDummy(1))
    for event_type in (DamageDummy, DummyLossHealth):
        assert sum(e.value for e in resolution.iter_type(event_type)) == 1
    assert Dummy.damage == 1
    check_history(ES, [DummyLossHealth(1, result=1), DamageDummy(1, result=1)])


def test_two_events():
    for i in range(2):
        ES.resolve(DamageDummy(value=3))
    assert Dummy.damage == 6


def test_invalid_event():
    assert not list(ES.resolve(DamageDummy(value=0)).iter_type(DamageDummy))
    assert Dummy.damage == 0


def test_event_using_result_of_other_event():
    @dataclasses.dataclass
    class StaggeringAttack(Event[None]):
        strength: int

        def resolve(self) -> None:
            ES.resolve(
                MoveDummy(
                    sum(
                        e.result
                        for e in ES
                        .resolve(HitDummy(self.strength))
                        .iter_type(DamageDummy)
                    )
                )
            )

    Dummy.armor = 1

    ES.resolve(StaggeringAttack(2))

    assert Dummy.damage == 1
    assert Dummy.position == 1


def test_event_conditional_result_of_other_event():
    @dataclasses.dataclass
    class BloodThirstyAttack(Event[None]):
        strength: int

        def resolve(self) -> None:
            if ES.resolve(HitDummy(value=self.strength)).has_type(DummyLossHealth):
                ES.resolve(HitDummy(value=2))

    Dummy.armor = 1

    ES.resolve(BloodThirstyAttack(3))
    assert Dummy.damage == 3

    ES.resolve(BloodThirstyAttack(1))
    assert Dummy.damage == 3
