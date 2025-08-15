from events.eventsystem import ES, HookEffect, ReplacementEffect, hook_on
from events.tests.game_objects.units import Damage, Move, Unit


def test_standalone_hook():
    unit = Unit()

    class PositionOnDamageTracker(HookEffect[Damage]):
        def __init__(self, unit: Unit):
            self.unit = unit
            self.last_position = self.unit.position

        def resolve_hook_call(self, event: Damage):
            self.last_position = self.unit.position

    tracker = ES.register_effect(PositionOnDamageTracker(unit))

    assert tracker.last_position == 0

    ES.resolve(Move(unit, 1))
    assert tracker.last_position == 0

    ES.resolve(Damage(unit, 3))
    ES.resolve(Move(unit, 1))
    assert tracker.last_position == 1


def test_hook_on_replacement():
    unit = Unit()

    class DamageAmplifiedByLastMove(ReplacementEffect[Damage]):
        priority = 0

        def __init__(self, unit: Unit):
            self.unit = unit
            self.move_amount = 0

        @hook_on(Move)
        def on_move_hook(self, event: Move) -> None:
            self.move_amount = event.amount

        def resolve(self, event: Damage) -> None:
            ES.resolve(event.branch(amount=event.amount + self.move_amount))

    ES.register_effect(DamageAmplifiedByLastMove(unit))

    ES.resolve(Damage(unit, 1))
    assert unit.health == 9
    assert unit.position == 0

    for i in range(1, 3):
        ES.resolve(Move(unit, i))
    ES.resolve(Damage(unit, 1))
    assert unit.health == 6
    assert unit.position == 3
