from events.eventsystem import ES
from game.core import (
    GS,
    ActivatedAbilityFacet,
    ActiveUnitContext,
    Cone,
    ConsecutiveAdjacentHexes,
    DamageSignature,
    EnergyCost,
    ExclusiveCost,
    Hex,
    HexHexes,
    HexRing,
    HexStatus,
    HexStatusSignature,
    MeleeAttackFacet,
    MovementCost,
    NOfUnits,
    NoTargetActivatedAbility,
    OneOfHexes,
    RadiatingLine,
    RangedAttackFacet,
    SingleAllyActivatedAbility,
    SingleEnemyActivatedAbility,
    SingleHexTargetActivatedAbility,
    SingleTargetActivatedAbility,
    TargetProfile,
    Tree,
    TreeNode,
    TriHexTargetActivatedAbility,
    Unit,
    UnitBlueprint,
    UnitStatus,
    UnitStatusSignature,
    is_vision_obstructed_for_unit_at,
    line_of_sight_obstructed_for_unit,
)
from game.effects.hooks import AdjacencyHook
from game.events import (
    ApplyHexStatus,
    ApplyStatus,
    Damage,
    DispelStatus,
    ExhaustUnit,
    GainEnergy,
    Heal,
    Hit,
    Kill,
    ModifyMovementPoints,
    MoveUnit,
    QueueUnitForActivation,
    ReadyUnit,
    SpawnUnit,
)
from game.statuses.dispel import dispel_all, dispel_from_unit
from game.statuses.hex_statuses import BurningTerrain, Glimpse, Shrine, Smoke, Soot
from game.statuses.unit_statuses import (
    Burn,
    BurstOfSpeed,
    Ephemeral,
    LuckyCharm,
    Panicked,
    Rooted,
    Staggered,
    Terror,
)
from game.values import DamageType, Size, StatusIntention


class Bloom(NoTargetActivatedAbility):
    cost = EnergyCost(2)

    def perform(self, target: None) -> None:
        for unit in GS.map.get_neighboring_units_off(self.parent):
            ES.resolve(Heal(unit, 1))
        ES.resolve(Kill(self.parent))


class Grow(NoTargetActivatedAbility):
    cost = EnergyCost(2)

    def perform(self, target: None) -> None:
        ES.resolve(Heal(self.parent, 1))


class HealBeam(SingleAllyActivatedAbility):
    """
    Target other allied unit within 2 range LoS. Heals 2.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 2))


class GreaseTheGears(SingleAllyActivatedAbility):
    """
    Target other allied unit 1 range. Kills the target. If it does, heal this unit 2, and it restores 2 energy.
    If the target unit was ready, this unit gains +1 movement point.
    """

    range = 1
    can_target_self = False
    combinable = True
    max_activations = None

    def perform(self, target: Unit) -> None:
        movement_bonus = 1 if not target.exhausted and GS.active_unit_context else 0
        if any(
            kill_event.unit == target
            for kill_event in ES.resolve(Kill(target)).iter_type(Kill)
        ):
            ES.resolve(Heal(self.parent, 2))
            ES.resolve(GainEnergy(self.parent, 2, source=self))
            ES.resolve(ModifyMovementPoints(self.parent, movement_bonus))


class NothingStopsTheMail(NoTargetActivatedAbility):
    """Kills this unit."""

    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.parent))


class SelfDestruct(NoTargetActivatedAbility):
    """Kills this unit."""

    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.parent))


class InducePanic(SingleEnemyActivatedAbility):
    """
    Target enemy unit within 2 range LoS. Applies <panicked> for 2 rounds.
    """

    range = 2
    cost = MovementCost(2) | EnergyCost(4)

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, UnitStatusSignature(Panicked, self, duration=2)))


class Vault(SingleTargetActivatedAbility):
    """
    Moves this unit to the other side of target adjacent unit. If it did, and the target unit was
    an enemy, apply <staggered> to it.
    """

    cost = MovementCost(1)
    range = 1
    combinable = True
    max_activations = None

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        target_position = GS.map.position_off(target)
        difference = target_position - GS.map.position_off(self.parent)
        target_hex = GS.map.hexes.get(target_position + difference)
        if target_hex and target_hex.can_move_into(self.parent):
            if (
                any(
                    e.result
                    for e in ES.resolve(MoveUnit(self.parent, target_hex)).iter_type(
                        MoveUnit
                    )
                )
                and target.controller != self.parent.controller
            ):
                ES.resolve(ApplyStatus(target, UnitStatusSignature(Staggered, self)))


class BatonPass(SingleTargetActivatedAbility):
    """
    Target different allied unit within 1 range that wasn't adjacent to this unit
    at the beginning of this units turn. Applies <burst_of_speed> to the target unit.
    """

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.parent)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def can_target_unit(self, unit: Unit) -> bool:
        return (
            unit.controller == self.parent.controller
            and unit != self.parent
            and unit not in self.adjacency_hook.adjacent_units
        )

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(BurstOfSpeed, self, stacks=1))
        )


class SummonScarab(SingleHexTargetActivatedAbility):
    """
    Target visible empty space within 3 range LoS. Summons an exhausted Scarab
    (2 health, 2 speed, 1 armor, 1 sight, S, 2 attack damage with 1 movement cost) with <ephemeral> for 3 rounds.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 3

    # TODO common logic? or flag on SingleHexTargetActivatedAbility?
    def can_target_hex(self, hex_: Hex) -> bool:
        return (unit := GS.map.unit_on(hex_)) is None or unit.is_hidden_for(
            self.parent.controller
        )

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["scarab"],
                controller=self.parent.controller,
                space=target,
                exhausted=True,
                with_statuses=[UnitStatusSignature(Ephemeral, self, duration=3)],
            )
        )


class Sweep(ActivatedAbilityFacet[list[Hex]]):
    """
    Target length 3 adjacent arc. Deals 4 melee damage to units on hexes.
    """

    cost = MovementCost(1)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return ConsecutiveAdjacentHexes(GS.map.hex_off(self.parent), 1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(4, self, DamageType.MELEE)))


class Stare(ActivatedAbilityFacet[list[Hex]]):
    """
    Target radiating line length 4. Applies <glimpse> to hexes sequentially, starting from the hex closest to this unit, until a hex blocks vision.
    """

    combinable = True

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return RadiatingLine(
            GS.map.hex_off(self.parent),
            list(GS.map.get_neighbors_off(self.parent)),
            4,
        )

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(ApplyHexStatus(h, HexStatusSignature(Glimpse, self)))
            if is_vision_obstructed_for_unit_at(self.parent, h.position):
                break


class Jaunt(ActivatedAbilityFacet[Hex]):
    """Teleports to target hex within 4 range NLoS."""

    cost = EnergyCost(3)
    combinable = True

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := list(GS.map.get_hexes_within_range_off(self.parent, 4)):
            return OneOfHexes(hexes)

    def perform(self, target: Hex) -> None:
        ES.resolve(MoveUnit(self.parent, target))


class Jump(ActivatedAbilityFacet[Hex]):
    """Teleports to target hex within 2 range NLoS."""

    cost = EnergyCost(2) | ExclusiveCost()

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := list(GS.map.get_hexes_within_range_off(self.parent, 2)):
            return OneOfHexes(hexes)

    def perform(self, target: Hex) -> None:
        ES.resolve(MoveUnit(self.parent, target))


class Rouse(SingleTargetActivatedAbility):
    cost = MovementCost(1) | EnergyCost(3)
    range = 3
    requires_los = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        # TODO make it not able to skip?
        ES.resolve(QueueUnitForActivation(target))


class SummonBees(SingleHexTargetActivatedAbility):
    cost = MovementCost(2) | EnergyCost(2)
    range = 2

    def can_target_hex(self, hex_: Hex) -> bool:
        return (unit := GS.map.unit_on(hex_)) is None or unit.is_hidden_for(
            self.parent.controller
        )

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["bee_swarm"],
                controller=self.parent.controller,
                space=target,
                with_statuses=[UnitStatusSignature(Ephemeral, self, duration=1)],
            )
        )


class StimulatingInjection(SingleTargetActivatedAbility):
    """
    Target other unit within 1 range.
    Deals 1 pure damage and readies the target.
    This unit dies.
    """

    range = 1
    cost = EnergyCost(3)

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.PURE)))
        ES.resolve(ReadyUnit(target))
        # TODO sacrifice as a cost?
        ES.resolve(Kill(self.parent))


class Suplex(SingleTargetActivatedAbility):
    """
    Target small or medium adjacent unit. Deals 3 melee damage, and moves the target to the other side of this unit.
    """

    range = 1
    cost = MovementCost(2) | EnergyCost(3)

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent and unit.size.g() < Size.LARGE

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(3, self, DamageType.MELEE)))
        own_position = GS.map.position_off(self.parent)
        if target_hex := GS.map.hexes.get(
            own_position + (own_position - GS.map.position_off(target))
        ):
            ES.resolve(MoveUnit(target, target_hex))


class Lasso(SingleEnemyActivatedAbility):
    """
    Target enemy unit within 2 range. Applies <rooted> for 1 round.
    """

    range = 2
    cost = MovementCost(2) | EnergyCost(3)
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, UnitStatusSignature(Rooted, self, duration=1)))


class Showdown(SingleEnemyActivatedAbility):
    """
    Target enemy unit within 3 range LoS. This unit hits the target with its primary ranged attack twice.
    If the target isn't exhausted, and it has a primary ranged attack, and it can hit this unit with
    that attack, it does and is exhausted. If it does not have a primary ranged attack, but it has
    a primary melee attack that can hit this unit, it uses that instead.
    """

    range = 3
    cost = ExclusiveCost() | EnergyCost(3)

    def perform(self, target: Unit) -> None:
        if attack := self.parent.get_primary_attack(RangedAttackFacet):
            for _ in range(2):
                ES.resolve(Hit(attacker=self.parent, defender=target, attack=attack))

        if not target.exhausted:
            for attack_type in (RangedAttackFacet, MeleeAttackFacet):
                if (
                    (defender_attack := target.get_primary_attack(attack_type))
                    and self.parent
                    in
                    # TODO yikes
                    defender_attack.get_legal_targets(ActiveUnitContext(target, 1))
                ):
                    ES.resolve(
                        Hit(
                            attacker=target,
                            defender=self.parent,
                            attack=defender_attack,
                        )
                    )
                    ES.resolve(ExhaustUnit(target))
                    break


class RaiseShrine(SingleHexTargetActivatedAbility):
    """
    Target hex within 1 range. Applies status <shrine>.
    """

    cost = MovementCost(2) | EnergyCost(3)

    def perform(self, target: Hex) -> None:
        ES.resolve(ApplyHexStatus(target, HexStatusSignature(Shrine, self)))


class GrantCharm(SingleAllyActivatedAbility):
    """
    Target different allied unit within 1 range. Applies <lucky_charm> for 3 rounds.
    """

    can_target_self = False
    cost = EnergyCost(2)

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(LuckyCharm, self, duration=3))
        )


class ChokingSoot(ActivatedAbilityFacet[list[Hex]]):
    """
    Target hex circle size 2, center within 2 range NLoS.
    Applies <soot> to hexes for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(4)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if hexes := [
            _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, 2)
        ]:
            return HexHexes(hexes, 1)

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(ApplyHexStatus(_hex, HexStatusSignature(Soot, self, duration=2)))


class SmokeCanister(ActivatedAbilityFacet[list[Hex]]):
    """
    Target hex circle size 2, center within 2 range NLoS.
    Applies <smoke> for 2 rounds.
    """

    cost = EnergyCost(3)
    combinable = True

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if hexes := [
            _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, 2)
        ]:
            return HexHexes(hexes, 1)

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(
                ApplyHexStatus(_hex, HexStatusSignature(Smoke, self, duration=2))
            )


class Terrorize(SingleEnemyActivatedAbility):
    """
    Target enemy unit within 4 range LoS. Applies <terror> for 2 rounds.
    """

    range = 4
    cost = MovementCost(2) | EnergyCost(5)

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, UnitStatusSignature(Terror, self, duration=2)))


class Scorch(ActivatedAbilityFacet[list[Hex]]):
    """
    Target length 3 adjacent arc. Deals 3 ranged damage and applies 2 stacks of <burn> to units on hexes.
    """

    cost = MovementCost(1) | EnergyCost(3)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return ConsecutiveAdjacentHexes(GS.map.hex_off(self.parent), 1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.AOE)))
                ES.resolve(ApplyStatus(unit, UnitStatusSignature(Burn, self, stacks=2)))


class FlameWall(ActivatedAbilityFacet[list[Hex]]):
    """
    Target length 3 radiating line. Applies 2 stacks of <burn> to each unit on hexes, and 1 stack of <burning_terrain> to the hex for 3 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return RadiatingLine(
            GS.map.hex_off(self.parent),
            list(GS.map.get_neighbors_off(self.parent)),
            3,
        )

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(
                ApplyHexStatus(
                    h,
                    HexStatusSignature(BurningTerrain, self, stacks=1, duration=3),
                )
            )
            if unit := GS.map.unit_on(h):
                ES.resolve(ApplyStatus(unit, UnitStatusSignature(Burn, self, stacks=2)))


class FlameThrower(ActivatedAbilityFacet[list[Hex]]):
    """
    Target 1-1-3 arc lengths radiating cone.
    Applies 1 stacks of <burn> to each unit on hexes, and 1 stack of <burning_terrain> to the hex for 2 rounds.
    """

    cost = EnergyCost(3)

    # TODO variable length cone?
    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return Cone(
            GS.map.hex_off(self.parent),
            list(GS.map.get_neighbors_off(self.parent)),
            [0, 0, 1],
        )

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(
                ApplyHexStatus(
                    h,
                    HexStatusSignature(BurningTerrain, self, stacks=1, duration=2),
                )
            )
            if unit := GS.map.unit_on(h):
                ES.resolve(ApplyStatus(unit, UnitStatusSignature(Burn, self, stacks=1)))


class VitalityTransfer(ActivatedAbilityFacet):
    """
    Target two allied units within 3 range LoS.
    Transfers health from the second to the first unit.
    Amount transferred is the minimum of 3, how much the recipient is missing, and how much the donor can give without dying.
    """

    cost = MovementCost(1) | EnergyCost(2)

    def get_target_profile(self) -> TargetProfile[list[Unit]] | None:
        if (
            len(
                # TODO some common logic for this trash
                units := [
                    unit
                    for unit in GS.map.get_units_within_range_off(self.parent, 3)
                    if unit.controller == self.parent.controller
                    and unit.is_visible_to(self.parent.controller)
                    and not line_of_sight_obstructed_for_unit(
                        self.parent,
                        GS.map.position_off(self.parent),
                        GS.map.position_off(unit),
                    )
                ]
            )
            >= 2
        ):
            return NOfUnits(units, 2, ["select recipient", "select donor"])

    def perform(self, target: list[Unit]) -> None:
        recipient, donor = target
        available_health = min(donor.health - 1, recipient.damage, 3)
        if available_health:
            # TODO yikes should be an event, but unclear what it should be,
            #  since we don't want it to be damage i think.
            donor.damage += available_health
            ES.resolve(Heal(recipient, available_health))


class Shove(SingleTargetActivatedAbility):
    """
    Moves target adjacent unit one space away from this unit. If it is staggered, this unit gains 1 movement point.
    """

    cost = MovementCost(1) | EnergyCost(2)
    range = 1
    combinable = True

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        target_position = GS.map.position_off(target)
        ES.resolve(
            MoveUnit(
                target,
                GS.map.hexes.get(
                    target_position
                    + (target_position - GS.map.position_off(self.parent))
                ),
            )
        )
        if any(isinstance(status, Staggered) for status in target.statuses):
            ES.resolve(ModifyMovementPoints(self.parent, 1))


class Poof(SingleHexTargetActivatedAbility):
    """Applies Smoke to the current position of this unit for 1 round, and moves this unit to target adjacent hex."""

    cost = EnergyCost(2)
    combinable = True
    requires_los = False
    requires_vision = False

    def can_target_hex(self, hex_: Hex) -> bool:
        return hex_.can_move_into(self.parent)

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                GS.map.hex_off(self.parent),
                HexStatusSignature(Smoke, self, duration=1),
            )
        )
        ES.resolve(MoveUnit(self.parent, target))


class VenomousSpine(SingleEnemyActivatedAbility):
    """
    Target enemy unit 2 range LoS. Applies <debilitating_venom> for 2 rounds and <parasite>.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(UnitStatus.get("parasite"), self))
        )
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(
                    UnitStatus.get("debilitating_venom"), self, duration=2
                ),
            )
        )


class Scry(SingleHexTargetActivatedAbility):
    """
    Target hex within 6 range NLoS. Applies <revealed> for 1 round.
    """

    cost = EnergyCost(2)
    range = 6
    requires_los = False
    requires_vision = False

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                target, HexStatusSignature(HexStatus.get("revealed"), self, duration=1)
            )
        )


class ShrinkRay(SingleTargetActivatedAbility):
    """
    Target unit within 2 range LoS. Deals 1 ranged damage and applies 1 stack of <shrunk> for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.RANGED)))
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(
                    UnitStatus.get("shrunk"), self, stacks=1, duration=2
                ),
            )
        )


class AssembleTheDoombot(SingleHexTargetActivatedAbility):
    """
    Target adjacent visible empty hex. Applies <doombot_scaffold> to hex.
    If it already has <doombot_scaffold>, instead dispel it, and spawn an exhausted Doombot 3000 with <ephemeral> for 4 rounds.
    """

    cost = ExclusiveCost() | EnergyCost(4)
    range = 1

    def can_target_hex(self, hex_: Hex) -> bool:
        return not GS.map.unit_on(hex_)

    def perform(self, target: Hex) -> None:
        if statuses := target.get_statuses(HexStatus.get("doombot_scaffold")):
            for status in statuses:
                ES.resolve(DispelStatus(target, status))
            ES.resolve(
                SpawnUnit(
                    UnitBlueprint.registry["doombot_3000"],
                    self.parent.controller,
                    target,
                    exhausted=True,
                    with_statuses=[
                        UnitStatusSignature(
                            UnitStatus.get("ephemeral"), self, duration=4
                        )
                    ],
                )
            )
        else:
            ES.resolve(
                ApplyHexStatus(
                    target, HexStatusSignature(HexStatus.get("doombot_scaffold"), self)
                )
            )


class Translocate(ActivatedAbilityFacet):
    """
    Target adjacent unit, and a hex within 1 range of that unit. Moves the unit to the hex.
    """

    cost = EnergyCost(2)
    combinable = True

    def get_target_profile(self) -> TargetProfile[list[Unit | Hex]] | None:
        if units := [
            (
                unit,
                TreeNode(
                    [(h, None) for h in GS.map.get_neighbors_off(unit)], "select hex"
                ),
            )
            for unit in GS.map.get_units_within_range_off(self.parent, 1)
            if unit.is_visible_to(self.parent.controller)
        ]:
            return Tree(TreeNode(units, "select unit"))

    def perform(self, target: list[Hex | Unit]) -> None:
        unit, to_ = target
        ES.resolve(MoveUnit(unit, to_))


class InkRing(ActivatedAbilityFacet):
    """
    Target size hex ring size 2, center within 3 range NloS.
    Applies <blinded> for 3 rounds.
    """

    cost = EnergyCost(3)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if hexes := [
            _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, 3)
        ]:
            return HexRing(hexes, 1)

    def perform(self, target: list[Hex]) -> None:
        for unit in GS.map.units_on(target):
            ES.resolve(
                ApplyStatus(
                    unit,
                    UnitStatusSignature(UnitStatus.get("blinded"), self, duration=3),
                )
            )


class MalevolentStare(SingleEnemyActivatedAbility):
    """
    Target enemy unit within 3 range LoS. Dispels all buffs and applies <silenced> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 3

    def perform(self, target: Unit) -> None:
        dispel_from_unit(target, StatusIntention.BUFF)
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(UnitStatus.get("silenced"), self, duration=2),
            )
        )


class IronBlessing(SingleAllyActivatedAbility):
    """
    Target other allied unit within 1 range. Applies <armored> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 1
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, UnitStatusSignature(UnitStatus.get("armored"), self, duration=2)
            )
        )


class Hitch(SingleAllyActivatedAbility):
    """
    Target different adjacent allied unit. Applies <hitched>.
    """

    cost = EnergyCost(3)
    range = 1
    can_target_self = False
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(UnitStatus.get("hitched"), self))
        )


class CoordinatedManeuver(ActivatedAbilityFacet[list[Unit]]):
    """
    Target 1 or 2 other ready allied units within 2 range LoS. Activates them.
    """

    cost = EnergyCost(3) | MovementCost(1)

    def get_target_profile(self) -> TargetProfile[list[Unit]] | None:
        if units := [
            unit
            for unit in GS.map.get_units_within_range_off(self.parent, 2)
            if unit.controller == self.parent.controller
            and unit != self.parent
            and not unit.exhausted
            and not line_of_sight_obstructed_for_unit(
                self.parent,
                GS.map.position_off(self.parent),
                GS.map.position_off(unit),
            )
        ]:
            return NOfUnits(units, 2, ["select target", "select target"], min_count=1)

    def perform(self, target: list[Unit]) -> None:
        for unit in target:
            ES.resolve(QueueUnitForActivation(unit))


class LayMine(SingleHexTargetActivatedAbility):
    """
    Target unoccupied hex within 2 range. Applies <mine>.
    """

    cost = EnergyCost(2) | MovementCost(1)
    combinable = True

    def can_target_hex(self, hex_: Hex) -> bool:
        return not GS.map.unit_on(hex_)

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(target, HexStatusSignature(HexStatus.get("mine"), self))
        )


class SanctifyGrounds(SingleHexTargetActivatedAbility):
    """Target hex within 1 range. Dispels hex statuses."""

    cost = EnergyCost(2)

    def perform(self, target: Hex) -> None:
        dispel_all(target)


class Vomit(SingleHexTargetActivatedAbility):
    """
    Target adjacent hex. Deals aoe 5 damage.
    """

    cost = MovementCost(2)

    requires_vision = False

    def can_target_hex(self, hex_: Hex) -> bool:
        return hex_ != GS.map.hex_off(self.parent)

    def perform(self, target: Hex) -> None:
        if unit := GS.map.unit_on(target):
            ES.resolve(Damage(unit, DamageSignature(5, self, DamageType.AOE)))


class SludgeBelch(TriHexTargetActivatedAbility):
    """
    Target tri hex within 2 range NLoS.
    Applies <sludge> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(
                ApplyHexStatus(
                    _hex, HexStatusSignature(HexStatus.get("sludge"), self, duration=2)
                )
            )


class HandGrenade(TriHexTargetActivatedAbility):
    """
    Target tri hex within 2 range NLoS.
    Deals 3 aoe damage.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            if unit := GS.map.unit_on(_hex):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.AOE)))


class FlashBang(TriHexTargetActivatedAbility):
    """
    Target tri hex within 2 range NLoS.
    Applies <blinded> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            if unit := GS.map.unit_on(_hex):
                ES.resolve(
                    ApplyStatus(
                        unit,
                        UnitStatusSignature(
                            UnitStatus.get("blinded"), self, duration=2
                        ),
                    )
                )


class SmokeGrenade(TriHexTargetActivatedAbility):
    """
    Target tri hex within 2 range NLoS.
    Applies <smoke> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(
                ApplyHexStatus(
                    _hex, HexStatusSignature(HexStatus.get("smoke"), self, duration=2)
                )
            )


class SowDiscord(TriHexTargetActivatedAbility):
    """
    Target tri hex within 3 range NLoS.
    Applies <paranoia> for 3 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    def perform(self, target: list[Hex]) -> None:
        for unit in GS.map.units_on(target):
            ES.resolve(
                ApplyStatus(
                    unit,
                    UnitStatusSignature(UnitStatus.get("paranoia"), self, duration=3),
                )
            )


class Scorn(SingleEnemyActivatedAbility):
    """
    Target enemy unit within 2 range LoS.
    Applies <dishonorable_coward> for 4 rounds.
    """

    cost = EnergyCost(2)
    range = 2

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(
                    UnitStatus.get("dishonorable_coward"), self, duration=4
                ),
            )
        )


class SpurIntoRage(SingleTargetActivatedAbility):
    """
    Target other unit within 2 range LoS.
    Applies <senseless_rage> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 2

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(UnitStatus.get("senseless_rage"), self, duration=2),
            )
        )


class ConstructTurret(SingleHexTargetActivatedAbility):
    """
    Target visible empty space within 1 range.
    Summons an exhausted Sentry Turret with <ephemeral> for 4 rounds.
    """

    cost = MovementCost(2) | EnergyCost(4)

    def can_target_hex(self, hex_: Hex) -> bool:
        return (unit := GS.map.unit_on(hex_)) is None or unit.is_hidden_for(
            self.parent.controller
        )

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                UnitBlueprint.get_class("sentry_turret"),
                self.parent.controller,
                target,
                exhausted=True,
                with_statuses=[
                    UnitStatusSignature(UnitStatus.get("ephemeral"), self, duration=4)
                ],
            )
        )


class FixErUp(SingleTargetActivatedAbility):
    """
    Target adjacent allied unit with 1 or more base armor or Sentry Turret.
    Heals 2.
    """

    name = "Fix 'er Up"
    cost = EnergyCost(2) | MovementCost(1)

    def can_target_unit(self, unit: Unit) -> bool:
        return (
            unit != self.parent
            and unit.controller == self.parent.controller
            and (
                unit.armor.get_base() > 0
                or unit.blueprint == UnitBlueprint.get_class("sentry_turret")
            )
        )

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 2))


class TurboTune(SingleTargetActivatedAbility):
    """
    Target adjacent allied unit with 1 or more base armor.
    Applies <turbo> for 2 rounds.
    """

    cost = EnergyCost(2) | MovementCost(2)

    def can_target_unit(self, unit: Unit) -> bool:
        return (
            unit != self.parent
            and unit.controller == self.parent.controller
            and unit.armor.get_base() > 0
        )

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, UnitStatusSignature(UnitStatus.get("turbo"), self, duration=2)
            )
        )
