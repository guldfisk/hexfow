from events.eventsystem import EventSystem, Event
from events.tests.game_objects.dummy import (
    HitDummy,
    Dummy,
    DummyLossHealth,
    DamageAlsoMoves,
    MoveToDamage,
)


def test_event_searches_history(es: EventSystem):
    class EchoAttack(Event[None]):

        def resolve(self, es: EventSystem) -> None:
            if previous_hit := es.last_event_of_type(HitDummy):
                es.resolve(HitDummy(previous_hit.value))

    es.resolve(EchoAttack())
    assert es.history == [EchoAttack()]
    assert Dummy.damage == 0

    es.resolve(HitDummy(1))
    assert Dummy.damage == 1

    es.resolve(EchoAttack())
    assert Dummy.damage == 2

    es.resolve(HitDummy(2))
    assert Dummy.damage == 4

    es.resolve(EchoAttack())
    assert Dummy.damage == 6


def test_event_searches_historic_event_children(es: EventSystem):
    class EchoPainAttack(Event[None]):

        def resolve(self, es: EventSystem) -> None:
            if previous_hit := es.last_event_of_type(HitDummy):
                es.resolve(
                    HitDummy(
                        sum(e.value for e in previous_hit.iter_type(DummyLossHealth))
                    )
                )

    Dummy.armor = 1

    es.resolve(EchoPainAttack())
    assert es.history == [EchoPainAttack()]
    assert Dummy.damage == 0

    es.resolve(HitDummy(3))
    assert Dummy.damage == 2

    es.resolve(EchoPainAttack())
    assert Dummy.damage == 3

    es.resolve(EchoPainAttack())
    assert Dummy.damage == 3

    es.register_effect(DamageAlsoMoves())
    es.register_effect(MoveToDamage())

    Dummy.damage = 0

    es.resolve(HitDummy(3))
    assert Dummy.damage == 4

    es.resolve(EchoPainAttack())
    assert Dummy.damage == 10
