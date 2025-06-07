from events.eventsystem import ES
from game.game.core import (
    NoTargetActivatedAbility,
    GS,
    Unit,
    SingleAllyActivatedAbility,
    SingleEnemyActivatedAbility,
)
from game.game.events import Kill, Heal, ApplyStatus
from game.game.statuses import Panicked


class Bloom(NoTargetActivatedAbility):
    energy_cost = 2

    def perform(self, target: None) -> None:
        for unit in GS().map.get_neighboring_units_off(self.owner):
            ES.resolve(Heal(unit, 1))
        ES.resolve(Kill(self.owner))


class Grow(NoTargetActivatedAbility):
    energy_cost = 2

    def perform(self, target: None) -> None:
        ES.resolve(Heal(self.owner, 1))


class HealBeam(SingleAllyActivatedAbility):
    movement_cost = 1
    range = 2
    energy_cost = 2
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 3))


class Suicide(NoTargetActivatedAbility):
    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.owner))


class InducePanic(SingleEnemyActivatedAbility):
    movement_cost = 1
    range = 3
    energy_cost = 3

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=target, status_type=Panicked, by=self.owner.controller, duration=3
            )
        )
