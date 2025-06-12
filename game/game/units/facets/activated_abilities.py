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
    line_of_sight_obstructed_for_unit,
    RangedAttackFacet,
    MeleeAttackFacet,
)
from game.game.damage import DamageSignature
from game.game.decisions import TargetProfile, O
from game.game.events import (
    Kill,
    Heal,
    ApplyStatus,
    MoveUnit,
    SpawnUnit,
    Damage,
    QueueUnitForActivation,
    SimpleAttack,
)
from game.game.statuses import Panicked, BurstOfSpeed, Staggered, Ephemeral, Rooted
from game.game.units.facets.hooks import AdjacencyHook
from game.game.values import DamageType, Size


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
            and not line_of_sight_obstructed_for_unit(
                self.owner,
                GS().map.position_of(self.owner).position,
                _hex.position,
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
            if spawn_event.result:
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


# telepath {7pp} x1
# health 5, movement 3, sight 0, energy 5, M
# rouse
#     ability 3 energy
#     target other unit 3 range NLoS
#     -1 movement
#     activates target
# pacify
#     ability 3 energy
#     target other unit 3 range NLoS
#     -2 movement
#     applies pacified for 1 round
#         disarmed
#         +1 energy regen
# turn outwards
#     ability 3 energy
#     target other unit 2 range NLoS
#     -1 movement
#     applies far gazing for 2 rounds
#         +1 sight
#         cannot see adjacent hexes
# - adjacent enemy units also provide vision for this units controller


class Rouse(SingleTargetActivatedAbility):
    energy_cost = 3
    movement_cost = 1
    range = 3
    requires_los = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        # TODO make it not able to skip?
        ES.resolve(QueueUnitForActivation(target))


# bee shaman {7wrp} x2
# health 4, movement 3, sight 2, energy 3, S
# summon bees
#     ability 2 energy
#     target hex 2 range LoS, -2 movement
#     summons bee swarm with ephemeral duration 1 round
# royal jelly
#     ability 2 energy
#     target different allied unit 2 range LoS, -1 movement
#     heals 2 and restores 1 energy


class SummonBees(ActivatedAbilityFacet):
    movement_cost = 2
    energy_cost = 2

    # TODO common logic
    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := [
            _hex
            for _hex in GS().map.get_hexes_within_range_off(self.owner, 2)
            if GS().vision_map[self.owner.controller][_hex.position]
            and not line_of_sight_obstructed_for_unit(
                self.owner,
                GS().map.position_of(self.owner).position,
                _hex.position,
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
                blueprint=UnitBlueprint.registry["bee_swarm"],
                controller=self.owner.controller,
                space=target,
            )
        ).iter_type(SpawnUnit):
            ES.resolve(
                ApplyStatus(
                    unit=spawn_event.result,
                    status_type=Ephemeral,
                    by=self.owner.controller,
                    duration=1,
                )
            )


class StimulatingInjection(SingleTargetActivatedAbility):
    range = 1
    energy_cost = 3
    can_target_self = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, DamageType.TRUE)))
        # TODO event
        target.exhausted = False
        ES.resolve(Kill(self.owner))


# legendary wrestler {11pg} x1
# health 7, movement 3, sight 2, energy 4, M
# tackle
#     melee attack
#     2 damage
#     applies stumble
#         -1 movement point next activation
# from the top rope
#     melee attack
#     4 damage, -1 movement
#     +1 damage against units with stumble debuff
#     deals 2 non-lethal physical damage to this unit
# supplex
#     ability 3 energy, -2 movement
#     target M- adjacent unit
#     deals 3 melee damage and moves the target to the other side of this unit, if able.
# - caught in the match
#     enemies disengageging this units suffers -1 movement point
# - heel turn
#     when this unit receives 4 or more damage in a single instance, it gets, "they've got a still chari"
#         unstackable
#         +1 attack power


class Suplex(SingleTargetActivatedAbility):
    range = 1
    energy_cost = 3
    movement_cost = 2

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner and unit.size.g() < Size.LARGE

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(3)))
        own_position = GS().map.position_of(self.owner).position
        if target_hex := GS().map.hexes.get(
            own_position + (own_position - GS().map.position_of(target).position)
        ):
            ES.resolve(MoveUnit(target, target_hex))


# notorious outlaw
# health 5, movement 3, sight 2, energy 3, M
# twin revolvers
#     2x repeatable ranged attack
#     2 damage, 3 range, -1 movement
# lasso
#     combineable ability 3 energy
#     target enemy unit 2 range LoS
#     -2 movement
#     applies rooted for 1 round
# showdown
#     ability 3 energy
#     target enemy unit 3 range LoS
#     no movement
#     hits the targeted unit with primary ranged attack twice
#     if it is still alive, it will first try to hit with it's primary ranged attack if it has one, if it doesn't or can't,
#     it will try to hit with it's primary melee attack.
#     if it hits this way, exhaust it
# - dash
#     when this unit ends it's turn, it may move one space (irregardless of movement points)


class Lasso(SingleEnemyActivatedAbility):
    range = 2
    energy_cost = 3
    movement_cost = 2
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=target, status_type=Rooted, by=self.owner.controller, duration=1
            )
        )


class Showdown(SingleEnemyActivatedAbility):
    range = 3
    energy_cost = 3
    # TODO
    movement_cost = 3

    def perform(self, target: Unit) -> None:
        if attack := self.owner.get_primary_attack(RangedAttackFacet):
            for _ in range(2):
                ES.resolve(
                    SimpleAttack(attacker=self.owner, defender=target, attack=attack)
                )

        if not target.exhausted:
            for attack_type in (RangedAttackFacet, MeleeAttackFacet):
                if (
                    defender_attack := target.get_primary_attack(attack_type)
                ) and self.owner in defender_attack.get_legal_targets(None):
                    ES.resolve(
                        SimpleAttack(
                            attacker=target, defender=self.owner, attack=defender_attack
                        )
                    )
                    # TODO
                    target.exhausted = True
                    break
