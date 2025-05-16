from events.eventsystem import Event, ES
from events.tests.game_objects.dummy import (
    HitDummy,
    Dummy,
    DummyLossHealth,
    DamageAlsoMoves,
    MoveToDamage,
)


def test_event_searches_history():
    class EchoAttack(Event[None]):

        def resolve(self) -> None:
            if previous_hit := ES.last_event_of_type(HitDummy):
                ES.resolve(HitDummy(previous_hit.value))

    ES.resolve(EchoAttack())
    assert [e.name for e in ES.history] == [EchoAttack.name]
    assert Dummy.damage == 0

    ES.resolve(HitDummy(1))
    assert Dummy.damage == 1

    ES.resolve(EchoAttack())
    assert Dummy.damage == 2

    ES.resolve(HitDummy(2))
    assert Dummy.damage == 4

    ES.resolve(EchoAttack())
    assert Dummy.damage == 6


def test_event_searches_historic_event_children():
    class EchoPainAttack(Event[None]):

        def resolve(self) -> None:
            if previous_hit := ES.last_event_of_type(HitDummy):
                ES.resolve(
                    HitDummy(
                        sum(e.value for e in previous_hit.iter_type(DummyLossHealth))
                    )
                )

    Dummy.armor = 1

    ES.resolve(EchoPainAttack())
    # assert ES.history == [EchoPainAttack()]
    assert [e.name for e in ES.history] == [EchoPainAttack.name]
    assert Dummy.damage == 0

    ES.resolve(HitDummy(3))
    assert Dummy.damage == 2

    ES.resolve(EchoPainAttack())
    assert Dummy.damage == 3

    ES.resolve(EchoPainAttack())
    assert Dummy.damage == 3

    ES.register_effects(DamageAlsoMoves())
    ES.register_effects(MoveToDamage())

    Dummy.damage = 0

    ES.resolve(HitDummy(3))
    assert Dummy.damage == 4

    ES.resolve(EchoPainAttack())
    assert Dummy.damage == 10
