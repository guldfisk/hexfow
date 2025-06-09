from events.eventsystem import ES
from game.game.core import (
    NoTargetActivatedAbility,
    GS,
    Unit,
    SingleAllyActivatedAbility,
    SingleEnemyActivatedAbility,
    SingleTargetActivatedAbility,
    ActivatedAbilityFacet,
    Hex,
    OneOfHexes,
    UnitBlueprint,
    SelectConsecutiveAdjacentHexes,
    SelectRadiatingLine,
)
from game.game.damage import DamageSignature
from game.game.decisions import TargetProfile, O
from game.game.events import Kill, Heal, ApplyStatus, MoveUnit, SpawnUnit, Damage
from game.game.map.coordinates import line_of_sight_obstructed
from game.game.statuses import Panicked, BurstOfSpeed, Staggered, Ephemeral
from game.game.units.facets.hooks import AdjacencyHook
from game.game.values import DamageType


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


class SummonScarab(ActivatedAbilityFacet[Hex]):
    movement_cost = 2
    energy_cost = 3

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := [
            _hex
            for _hex in GS().map.get_hexes_within_range_off(self.owner, 3)
            if GS().vision_map[self.owner.controller][_hex.position]
            and not line_of_sight_obstructed(
                GS().map.position_of(self.owner).position,
                _hex.position,
                GS().vision_obstruction_map[self.owner.controller].get,
            )
            and (
                (unit := GS().map.unit_on(_hex)) is None
                or unit.is_hidden_for(self.owner.controller)
            )
        ]:
            return OneOfHexes(hexes)

    def perform(self, target: Hex) -> None:
        for spawn_event in ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["scarab"],
                controller=self.owner.controller,
                space=target,
                exhausted=True,
            )
        ).iter_type(SpawnUnit):
            # TODO right now this triggers schadenfreude, which makes fine sense,
            #  but is not necessarily immediately obvious, and was not what I
            #  intended to begin with. Could circumvent it, but would be pretty
            #  ugly. Mechanically seems cool, maybe just make sure it is clear
            #  from description, and maybe bump energy cost / reduce max energy.
            ES.resolve(
                ApplyStatus(
                    unit=spawn_event.result,
                    status_type=Ephemeral,
                    by=self.owner.controller,
                    duration=3,
                )
            )


# cyclops {15gg} x1
# health 11, movement 3, sight 1, L
# club
#     melee attack
#     5 damage
# sweep
#     aoe attack
#     aoe type 3 consecutive adjacent hexes
#     4 melee damage, -1 movement
# stare
#     combinable aoe ability
#         aoe type radiating line length 4 FoV propagation
#         reveals hexes this action


class Sweep(ActivatedAbilityFacet[list[Hex]]):
    movement_cost = 1

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return SelectConsecutiveAdjacentHexes(GS().map.position_of(self.owner), 1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS().map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, DamageType.MELEE)))


class Stare(ActivatedAbilityFacet[list[Hex]]):
    combinable = True

    def get_target_profile(self) -> TargetProfile[O] | None:
        return SelectRadiatingLine(GS().map.position_of(self.owner), 4)

    def perform(self, target: list[Hex]) -> None:
        # TODO reveal em'
        pass


class Jaunt(ActivatedAbilityFacet[Hex]):
    energy_cost = 3
    combinable = True

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := list(GS().map.get_hexes_within_range_off(self.owner, 4)):
            return OneOfHexes(hexes)

    def perform(self, target: Hex) -> None:
        ES.resolve(MoveUnit(self.owner, target))
