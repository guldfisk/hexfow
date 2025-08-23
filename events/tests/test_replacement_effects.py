from events.eventsystem import ES
from events.tests.game_objects.dummy import (
    AdditionalDamage,
    DamageAlsoMoves,
    DamageDummy,
    DamageToMove,
    DoubleDamage,
    Dummy,
    DummyLossHealth,
    MoveDummy,
    MoveToDamage,
    PreventDamage,
)


def test_replace():
    ES.register_effects(DoubleDamage())
    assert (
        sum(e.value for e in ES.resolve(DamageDummy(value=2)).iter_type(DamageDummy))
        == 4
    )
    assert Dummy.damage == 4


def test_multiple_same_replacement_effect():
    for _ in range(3):
        ES.register_effects(DoubleDamage())

    assert ES.resolve(DamageDummy(value=3))

    assert Dummy.damage == 24


def test_multiple_replaced_events():
    ES.register_effects(DoubleDamage())
    for _ in range(2):
        ES.resolve(DamageDummy(value=2))

    assert Dummy.damage == 8


def test_deregister_replace():
    ES.deregister_effect(ES.register_effect(DoubleDamage()))
    ES.resolve(DamageDummy(value=2))
    assert Dummy.damage == 2


def test_prevent_event():
    ES.register_effects(PreventDamage())
    assert not list(ES.resolve(DamageDummy(value=2)).iter_type(DamageDummy))
    assert Dummy.damage == 0


def test_replace_swap_event_type():
    ES.register_effects(DamageToMove())
    resolution = ES.resolve(DamageDummy(value=3))
    assert not list(resolution.iter_type(DamageDummy))
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 3
    assert Dummy.damage == 0
    assert Dummy.position == 3
    assert ES.history == [MoveDummy(distance=3, result=3)]


def test_double_swap():
    ES.register_effects(MoveToDamage())
    ES.register_effects(DamageToMove())
    resolution = ES.resolve(DamageDummy(3))
    assert not list(resolution.iter_type(MoveDummy))
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 3
    assert Dummy.damage == 3
    assert Dummy.position == 0
    assert ES.history == [DummyLossHealth(3, result=3), DamageDummy(3, result=3)]


def test_event_affected_by_multiple_different_replacements():
    ES.register_effects(AdditionalDamage())
    ES.register_effects(DoubleDamage())
    ES.resolve(DamageDummy(2))
    assert Dummy.damage == 5


def test_replacement_spawns_multiple_events():
    ES.register_effects(DamageAlsoMoves())
    resolution = ES.resolve(DamageDummy(1))
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 1
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 1
    assert Dummy.damage == 1
    assert Dummy.position == 1
    assert ES.history == [
        MoveDummy(1, result=1),
        DummyLossHealth(1, result=1),
        DamageDummy(1, result=1),
    ]


def test_replacement_spawns_multiple_events_multiple_times():
    for _ in range(2):
        ES.register_effects(DamageAlsoMoves())
    resolution = ES.resolve(DamageDummy(1))
    assert Dummy.damage == 1
    assert Dummy.position == 2
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 1
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 2
    assert ES.history == [
        MoveDummy(1, result=1),
        MoveDummy(1, result=1),
        DummyLossHealth(1, result=1),
        DamageDummy(1, result=1),
    ]

    resolution = ES.resolve(DamageDummy(1))
    assert Dummy.damage == 2
    assert Dummy.position == 4
    assert sum(e.value for e in resolution.iter_type(DamageDummy)) == 1
    assert sum(e.distance for e in resolution.iter_type(MoveDummy)) == 2
