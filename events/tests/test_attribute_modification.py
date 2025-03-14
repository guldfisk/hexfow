from debug_utils import dp
from events.eventsystem import EventSystem
from events.tests.game_objects.units import Unit, DoublePower, AddPowerIfEven, CapPower, ToughnessAtLeastPower, \
    AddPowerToToughness, AddToughnessToPower


def test_modifiable_attribute(es: EventSystem):
    unit = Unit(2)
    assert unit.power.get(es) == 2
    dp(Unit.power)
    dp(DoublePower.target)
    es.register_effect(DoublePower(unit))
    assert unit.power.get(es) == 4
    assert unit.power.get_base() == 2
    assert Unit(3).power.get(es) == 3


def test_deregister_modifiable_attribute(es: EventSystem):
    units = [Unit(v) for v in (1, 2)]
    effects = [es.register_effect(DoublePower(unit)) for unit in units]
    es.deregister_effect(effects[0])
    assert units[0].power.get(es) == 1
    assert units[1].power.get(es) == 4


def test_set_modifiable_attribute(es: EventSystem):
    unit = Unit(2)
    assert unit.power.get(es) == 2
    es.register_effect(DoublePower(unit))
    assert unit.power.get(es) == 4
    unit.power.set(3)
    assert unit.power.get(es) == 6


def test_attribute_modification_order(es: EventSystem):
    units = [Unit(2) for _ in range(3)]

    es.register_effect(DoublePower(units[0]))
    es.register_effect(DoublePower(units[0]))

    dp = es.register_effect(DoublePower(units[1]))
    es.register_effect(AddPowerIfEven(units[1]))

    es.register_effect(DoublePower(units[2]))
    cap = es.register_effect(CapPower(units[2], 3))
    es.register_effect(DoublePower(units[2]))

    assert units[0].power.get(es) == 8

    assert units[1].power.get(es) == 5
    units[1].power.set(1)
    assert units[1].power.get(es) == 3
    es.deregister_effect(dp)
    assert units[1].power.get(es) == 1

    assert units[2].power.get(es) == 3
    es.deregister_effect(cap)
    assert units[2].power.get(es) == 8


def test_dependant_attributes(es: EventSystem):
    unit = Unit(2, 1)
    es.register_effect(ToughnessAtLeastPower(unit))

    assert unit.toughness.get(es) == 2

    unit.toughness.set(3)
    assert unit.toughness.get(es) == 3

    es.register_effect(DoublePower(unit))
    assert unit.toughness.get(es) == 4


def test_circular_attribute_dependency(es: EventSystem):
    unit = Unit(2, 1)
    es.register_effect(AddPowerToToughness(unit))
    es.register_effect(AddToughnessToPower(unit))

    assert unit.power.get(es) == 5
    assert unit.toughness.get(es) == 4

    es.register_effect(CapPower(unit, 1))
    assert unit.power.get(es) == 1
    assert unit.toughness.get(es) == 2