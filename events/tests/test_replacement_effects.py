from debug_utils import dp
from events.eventsystem import EventSystem
from events.tests.game_objects.dummy import (
    DoubleDamage,
    DamageDummy,
    Dummy,
    PreventDamage,
    DamageToMove,
    MoveDummy,
    MoveToDamage,
    DummyLossHealth,
    AdditionalDamage,
    DamageAlsoMoves,
)


def test_replace(es: EventSystem):
    es.register_effect(DoubleDamage())
    assert (
        sum(
            e.value
            for e in es.resolve(DamageDummy(value=2)).iter_type(DamageDummy)
        )
        == 4
    )
    assert Dummy.damage == 4


def test_multiple_same_replacement_effect(es: EventSystem):
    for _ in range(3):
        es.register_effect(DoubleDamage())

    assert es.resolve(DamageDummy(value=3))

    assert Dummy.damage == 24


def test_multiple_replaced_events(es: EventSystem):
    es.register_effect(DoubleDamage())
    for _ in range(2):
        es.resolve(DamageDummy(value=2))

    assert Dummy.damage == 8


def test_deregister_replace(es: EventSystem):
    es.deregister_effect(es.register_effect(DoubleDamage()))
    es.resolve(DamageDummy(value=2))
    assert Dummy.damage == 2


def test_prevent_event(es: EventSystem):
    es.register_effect(PreventDamage())
    assert not list(es.resolve(DamageDummy(value=2)).iter_type(DamageDummy))
    assert Dummy.damage == 0


def test_replace_swap_event_type(es: EventSystem):
    es.register_effect(DamageToMove())
    resolution = es.resolve(DamageDummy(value=3))
    dp(resolution)
    assert not list(resolution.iter_type(DamageDummy))
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 3
    assert Dummy.damage == 0
    assert Dummy.position == 3
    assert es.history == [MoveDummy(distance=3, result=3)]


def test_double_swap(es: EventSystem):
    es.register_effect(MoveToDamage())
    es.register_effect(DamageToMove())
    resolution = es.resolve(DamageDummy(3))
    assert not list(resolution.iter_type(MoveDummy))
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 3
    assert Dummy.damage == 3
    assert Dummy.position == 0
    assert es.history == [DummyLossHealth(3, result=3), DamageDummy(3, result=3)]


def test_event_affected_by_multiple_different_replacements(es: EventSystem):
    es.register_effect(AdditionalDamage())
    es.register_effect(DoubleDamage())
    es.resolve(DamageDummy(2))
    assert Dummy.damage == 5


def test_replacement_spawns_multiple_events(es: EventSystem):
    es.register_effect(DamageAlsoMoves())
    resolution = es.resolve(DamageDummy(1))
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
    resolution = es.resolve(DamageDummy(1))
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
