from events.eventsystem import ES
from events.tests.game_objects.units import (
    AddPowerIfEven,
    AddPowerToToughness,
    AddToughnessToPower,
    CapPower,
    DoublePower,
    ToughnessAtLeastPower,
    Unit,
)


def test_modifiable_attribute():
    unit = Unit(2)
    assert unit.power.get(None) == 2
    ES.register_effects(DoublePower(unit))
    assert unit.power.get(None) == 4
    assert unit.power.get_base() == 2
    assert Unit(3).power.get(None) == 3


def test_deregister_modifiable_attribute():
    units = [Unit(v) for v in (1, 2)]
    effects = [DoublePower(unit) for unit in units]
    ES.register_effects(*effects)
    ES.deregister_effects(effects[0])
    assert units[0].power.get(None) == 1
    assert units[1].power.get(None) == 4


def test_set_modifiable_attribute():
    unit = Unit(2)
    assert unit.power.get(None) == 2
    ES.register_effects(DoublePower(unit))
    assert unit.power.get(None) == 4
    unit.power.set(3)
    assert unit.power.get(None) == 6


def test_attribute_modification_order():
    units = [Unit(2) for _ in range(3)]

    ES.register_effects(DoublePower(units[0]))
    ES.register_effects(DoublePower(units[0]))

    dp = ES.register_effect(DoublePower(units[1]))
    ES.register_effects(AddPowerIfEven(units[1]))

    ES.register_effects(DoublePower(units[2]))
    cap = ES.register_effect(CapPower(units[2], 3))
    ES.register_effects(DoublePower(units[2]))

    assert units[0].power.get(None) == 8

    assert units[1].power.get(None) == 5
    units[1].power.set(1)
    assert units[1].power.get(None) == 3
    ES.deregister_effects(dp)
    assert units[1].power.get(None) == 1

    assert units[2].power.get(None) == 3
    ES.deregister_effects(cap)
    assert units[2].power.get(None) == 8


def test_dependant_attributes():
    unit = Unit(2, 1)
    ES.register_effects(ToughnessAtLeastPower(unit))

    assert unit.toughness.get(None) == 2

    unit.toughness.set(3)
    assert unit.toughness.get(None) == 3

    ES.register_effects(DoublePower(unit))
    assert unit.toughness.get(None) == 4


def test_circular_attribute_dependency():
    unit = Unit(2, 1)
    ES.register_effects(AddPowerToToughness(unit))
    ES.register_effects(AddToughnessToPower(unit))

    assert unit.power.get(None) == 5
    assert unit.toughness.get(None) == 4

    ES.register_effects(CapPower(unit, 1))
    assert unit.power.get(None) == 1
    assert unit.toughness.get(None) == 2
