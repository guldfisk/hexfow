from events.eventsystem import StateModifierEffect, ES
from events.tests.game_objects.units import Unit, AttackShield, AttackShieldPenetrator


def test_method_modified():
    units = [Unit() for _ in range(3)]

    for unit in units[1:]:
        assert unit.can_be_attacked_by(units[0]) is True

    ES.register_effect(AttackShield(units[1], units[0]))

    assert units[1].can_be_attacked_by(units[0]) is False
    assert units[2].can_be_attacked_by(units[0]) is True


def test_prioritized_modifiers():
    units = [Unit() for _ in range(3)]

    for unit in units[1:]:
        ES.register_effect(AttackShield(unit, units[0]))

    for unit in units[1:]:
        assert unit.can_be_attacked_by(units[0]) is False

    ES.register_effect(AttackShieldPenetrator(units[0]))

    for unit in units[1:]:
        assert unit.can_be_attacked_by(units[0]) is True


class AttackMergable(StateModifierEffect[Unit, Unit, bool]):
    priority = 2
    target = Unit.can_be_attacked_by

    def modify(self, obj: Unit, request: Unit, value: bool) -> bool:
        return obj.can_merge_with(request)


def test_dependent_modifiers():
    units = [Unit() for _ in range(2)]

    ES.register_effect(AttackMergable())

    assert units[1].can_be_attacked_by(units[0]) is False

    class AllowMerging(StateModifierEffect[Unit, Unit, bool]):
        priority = 3
        target = Unit.can_merge_with

        def modify(self, obj: Unit, request: Unit, value: bool) -> bool:
            return True

    ES.register_effect(AllowMerging())

    assert units[1].can_be_attacked_by(units[0]) is True


def test_modifiers_circular_dependency():
    units = [Unit() for _ in range(2)]

    class MergeAttackable(StateModifierEffect[Unit, Unit, bool]):
        priority = 2
        target = Unit.can_merge_with

        def modify(self, obj: Unit, request: Unit, value: bool) -> bool:
            return obj.can_be_attacked_by(request)

    e = ES.register_effect(AttackMergable())
    ES.register_effect(MergeAttackable())

    assert units[1].can_be_attacked_by(units[0]) is True
    assert units[1].can_merge_with(units[0]) is False

    ES.deregister_effect(e)

    assert units[1].can_be_attacked_by(units[0]) is True
    assert units[1].can_merge_with(units[0]) is True
