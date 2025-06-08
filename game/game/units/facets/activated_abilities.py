from events.eventsystem import ES
from game.game.core import (
    NoTargetActivatedAbility,
    GS,
    Unit,
    SingleAllyActivatedAbility,
    SingleEnemyActivatedAbility,
    SingleTargetActivatedAbility,
)
from game.game.events import Kill, Heal, ApplyStatus, MoveUnit
from game.game.statuses import Panicked, BurstOfSpeed, Staggered
from game.game.units.facets.hooks import AdjacencyHook


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


class LeapFrog(SingleTargetActivatedAbility):
    movement_cost = 1
    range = 1
    energy_cost = 1
    combinable = True
    max_activations = None

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        target_position = GS().map.position_of(target).position
        difference = target_position - GS().map.position_of(self.owner).position
        target_hex = GS().map.hexes.get(target_position + difference)
        if target_hex and target_hex.can_move_into(self.owner):
            if (
                any(
                    e.result
                    for e in ES.resolve(MoveUnit(self.owner, target_hex)).iter_type(
                        MoveUnit
                    )
                )
                and target.controller != self.owner.controller
            ):

                ES.resolve(
                    ApplyStatus(
                        unit=target, status_type=Staggered, by=self.parent.controller
                    )
                )


class BatonPass(SingleTargetActivatedAbility):
    range = 1
    energy_cost = 1

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.owner)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def can_target_unit(self, unit: Unit) -> bool:
        return (
            unit.controller == self.owner.controller
            and unit != self.owner
            and unit not in self.adjacency_hook.adjacent_units
        )

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(unit=target, status_type=BurstOfSpeed, by=self.owner.controller)
        )
