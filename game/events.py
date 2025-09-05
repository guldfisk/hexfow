import contextlib
import dataclasses
import math
from collections import defaultdict
from typing import Iterable

from events.eventsystem import ES, Event, V
from game.core import (
    GS,
    ActivatedAbilityFacet,
    ActivateUnitOption,
    ActiveUnitContext,
    DamageSignature,
    DeployArmyDecisionPoint,
    EffortOption,
    G_decision_result,
    HasStatuses,
    Hex,
    HexStatus,
    HexStatusSignature,
    Landscape,
    LogLine,
    MeleeAttackFacet,
    MoveOption,
    NoTarget,
    OneOfHexes,
    OneOfUnits,
    OptionDecision,
    Player,
    RangedAttackFacet,
    SelectOptionDecisionPoint,
    SingleTargetAttackFacet,
    SkipOption,
    Source,
    Status,
    StatusSignature,
    TerrainProtectionRequest,
    TurnOrder,
    Unit,
    UnitBlueprint,
    UnitStatus,
    UnitStatusSignature,
    get_source_controller,
)
from game.values import DamageType, Resistance


# TODO yikes (have this rn so we can do stuff on kill before unit has it's effect
#  deregistered, making it's effects not trigger lmao).
@dataclasses.dataclass
class KillUpkeep(Event[None]):
    unit: Unit

    def resolve(self) -> V: ...


@dataclasses.dataclass
class Kill(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        with GS.log(LogLine([self.unit, "dies"])):
            for player in GS.turn_order:
                if self.unit.is_visible_to(player):
                    player.witness_kill(self.unit)
            ES.resolve(self.branch(KillUpkeep))
            GS.map.remove_unit(self.unit)
            for status in list(self.unit.statuses):
                status.remove()
            self.unit.deregister()


# TODO don't think this should be an event?
@dataclasses.dataclass
class CheckAlive(Event[bool]):
    unit: Unit

    def resolve(self) -> bool:
        # TODO common logic
        if self.unit.health <= 0 or not GS.map.hex_off(self.unit).is_passable_to(
            self.unit
        ):
            ES.resolve(Kill(self.unit))
            return False
        return True


@dataclasses.dataclass
class Heal(Event[int]):
    unit: Unit
    amount: int

    def is_valid(self) -> bool:
        return self.amount > 0 and self.unit.damage > 0

    def resolve(self) -> int:
        heal_amount = min(self.amount, self.unit.damage)
        with GS.log(LogLine([self.unit, f"is healed {heal_amount}"])):
            self.unit.damage -= heal_amount
        return heal_amount


@dataclasses.dataclass
class GainEnergy(Event[int]):
    unit: Unit
    amount: int
    source: Source
    allow_overflow: bool = False

    def is_valid(self) -> bool:
        return self.amount > 0 and (
            self.unit.energy < self.unit.max_energy.g() or self.allow_overflow
        )

    def resolve(self) -> int:
        amount = (
            self.amount
            if self.allow_overflow
            else max(min(self.amount, self.unit.max_energy.g() - self.unit.energy), 0)
        )
        with (
            GS.log(LogLine([self.unit, f"gains {amount} energy from", self.source]))
            if get_source_controller(self.source)
            else contextlib.nullcontext()
        ):
            self.unit.energy += amount
        return amount


@dataclasses.dataclass
class LoseEnergy(Event[int]):
    unit: Unit
    amount: int
    source: Source

    def is_valid(self) -> bool:
        return self.amount > 0 and self.unit.energy > 0

    def resolve(self) -> int:
        amount = min(self.amount, self.unit.energy)
        with GS.log(
            LogLine(
                [
                    self.unit,
                    f"loses {amount} energy",
                    *(("from", self.source) if self.source else ()),
                ]
            )
        ):
            self.unit.energy -= amount
        return amount


@dataclasses.dataclass
class SufferDamage(Event[int]):
    unit: Unit
    signature: DamageSignature

    def is_valid(self) -> bool:
        return self.signature.amount > 0

    def resolve(self) -> int:
        health_before = self.unit.health
        damage_dealt = self.unit.suffer_damage(self.signature)
        if damage_dealt:
            with GS.log(
                LogLine(
                    [
                        self.unit,
                        f"suffers {damage_dealt} damage",
                        *(
                            (f"({damage_dealt - health_before} overkill)",)
                            if damage_dealt > health_before
                            else ()
                        ),
                        *(
                            ("from", self.signature.source)
                            if self.signature.source
                            else ()
                        ),
                    ]
                )
            ):
                pass
        return min(health_before, damage_dealt)


@dataclasses.dataclass
class ReceiveDamage(Event[int]):
    unit: Unit
    signature: DamageSignature

    def is_valid(self) -> bool:
        return self.signature.amount > 0

    def resolve(self) -> int:
        defender_armor = self.unit.armor.g()
        damage = (
            self.signature.amount
            if self.signature.type == DamageType.PURE
            else max(
                self.signature.amount
                - min(defender_armor, max(defender_armor - self.signature.ap, 0)),
                0,
            )
        )
        match self.unit.get_resistance_against(self.signature):
            case Resistance.MINOR:
                damage = math.ceil(damage / 3 * 2)
            case Resistance.NORMAL:
                damage = math.ceil(damage / 2)
            case Resistance.MAJOR:
                damage = math.floor(damage / 2)
            case Resistance.IMMUNE:
                damage = 0
        ES.resolve(SufferDamage(self.unit, self.signature.with_damage(damage)))
        return damage


# TODO no reason to return value when we span child with that value
@dataclasses.dataclass
class Damage(Event[int]):
    unit: Unit
    signature: DamageSignature

    def is_valid(self) -> bool:
        return self.signature.amount > 0

    def resolve(self) -> int:
        damage = (
            self.signature.amount
            if self.signature.type == DamageType.PURE
            else max(
                self.signature.amount
                - (
                    self.unit.get_terrain_protection_for(
                        TerrainProtectionRequest(self.unit, self.signature)
                    )
                    if self.signature.type
                    in (DamageType.MELEE, DamageType.RANGED, DamageType.AOE)
                    else 0
                ),
                min(self.signature.amount, 1),
            )
        )
        ES.resolve(ReceiveDamage(self.unit, self.signature.with_damage(damage)))
        return damage


@dataclasses.dataclass
class Hit(Event[None]):
    attacker: Unit
    defender: Unit
    attack: SingleTargetAttackFacet

    def is_valid(self) -> bool:
        # TODO some way to formalize this?
        return self.attacker.on_map() and self.defender.on_map()

    def resolve(self) -> None:
        with GS.log(
            LogLine([self.attacker, "hits", self.defender, "with", self.attack]),
            LogLine([self.defender, "is hit with", self.attack]),
        ):
            self.attack.resolve_pre_damage_effects(self.defender)
            ES.resolve(
                Damage(
                    self.defender,
                    self.attack.get_damage_signature_against(self.defender),
                )
            )
            self.attack.resolve_post_damage_effects(self.defender)


@dataclasses.dataclass
class MeleeAttackAction(Event[None]):
    attacker: Unit
    defender: Unit
    attack: MeleeAttackFacet

    def resolve(self) -> None:
        defender_position = GS.map.hex_off(self.defender)
        attacker_position = GS.map.hex_off(self.attacker)
        movement_cost = GS.map.hex_off(self.defender).get_move_in_cost_for(
            self.attacker
        )
        move_out_penalty = MovePenalty(
            self.attacker,
            attacker_position,
            attacker_position.get_move_out_penalty_for(self.attacker),
            False,
        )
        move_in_penalty = MovePenalty(
            self.attacker,
            defender_position,
            defender_position.get_move_in_penalty_for(self.attacker),
            True,
        )
        ES.resolve(self.branch(Hit))
        ES.resolve(CheckAlive(self.defender))
        if (
            GS.active_unit_context.movement_points >= movement_cost
            and defender_position in self.attacker.get_potential_move_destinations(None)
            and (
                decision := GS.make_decision(
                    self.attacker.controller,
                    SelectOptionDecisionPoint(
                        [
                            SkipOption(target_profile=NoTarget()),
                            MoveOption(
                                target_profile=OneOfHexes(
                                    [defender_position, attacker_position]
                                )
                            ),
                        ],
                        explanation="follow up?",
                    ),
                )
            )
            and isinstance(decision.option, MoveOption)
            and decision.target == defender_position
        ):
            ES.resolve(MoveUnit(self.attacker, defender_position))
            GS.active_unit_context.movement_points -= movement_cost
            ES.resolve(move_out_penalty)
            ES.resolve(move_in_penalty)

        self.attack.get_cost().pay(GS.active_unit_context)


@dataclasses.dataclass
class RangedAttackAction(Event[None]):
    attacker: Unit
    defender: Unit
    attack: RangedAttackFacet

    def resolve(self) -> None:
        ES.resolve(self.branch(Hit))
        ES.resolve(CheckAlive(self.defender))
        self.attack.get_cost().pay(GS.active_unit_context)


def make_status_log_line(
    status: Status, signature: StatusSignature, recipient: Unit | Hex
) -> LogLine:
    return LogLine(
        [
            *(
                (f"{signature.stacks} stack{'s' if signature.stacks > 1 else ''} off",)
                if status.stacks
                else ()
            ),
            status,
            "is applied to",
            recipient,
            *(
                (f"for {status.duration} round{'s' if status.duration > 1 else ''}",)
                if status.duration
                else ()
            ),
        ]
    )


@dataclasses.dataclass
class ApplyStatus(Event[UnitStatus | None]):
    unit: Unit
    signature: UnitStatusSignature

    def is_valid(self) -> bool:
        return self.unit.on_map()

    def resolve(self) -> UnitStatus | None:
        if status := self.unit.add_status(self.signature):
            with GS.log(make_status_log_line(status, self.signature, self.unit)):
                return status
        return None


@dataclasses.dataclass
class ApplyHexStatus(Event[HexStatus | None]):
    space: Hex
    signature: HexStatusSignature

    def resolve(self) -> HexStatus | None:
        if status := self.space.add_status(self.signature):
            with GS.log(make_status_log_line(status, self.signature, self.space)):
                return status
        return None


@dataclasses.dataclass
class DispelStatus(Event[None]):
    owner: HasStatuses
    status: Status

    def is_valid(self) -> bool:
        return self.status.dispelable and any(
            s == self.status for s in self.owner.statuses
        )

    def resolve(self) -> None:
        for status in self.owner.statuses:
            if status == self.status:
                with GS.log(LogLine([status, "is dispelled from", self.owner])):
                    status.remove()
                break


@dataclasses.dataclass
class ActivateAbilityAction(Event[None]):
    unit: Unit
    ability: ActivatedAbilityFacet[G_decision_result]
    target: G_decision_result

    def resolve(self) -> None:
        with GS.log(
            LogLine([self.unit, "activates", self.ability, "targeting", self.target]),
            LogLine([self.unit, "activates", self.ability]),
        ):
            self.ability.perform(self.target)
            self.ability.get_cost().pay(GS.active_unit_context)


@dataclasses.dataclass
class MoveUnit(Event[Hex | None]):
    unit: Unit
    to_: Hex
    external: bool = False

    def resolve(self) -> Hex | None:
        from_ = None
        if self.to_.can_move_into(self.unit):
            from_ = self.to_.map.hex_off(self.unit)
            if not self.to_.map.move_unit_to(self.unit, self.to_):
                from_ = None

        if from_:
            if (
                self.to_.captured_by
                and self.to_.captured_by != self.unit.controller
                and self.unit.can_capture_objectives_on(self.to_)
            ):
                self.to_.captured_by = None
            # TODO hmm
            GS.update_vision()
            with GS.log(
                LogLine([self.unit, "moves into", self.to_]),
                LogLine([self.unit, "moves"]),
            ):
                return from_
        else:
            with GS.log(
                LogLine([self.unit, "fails to move into", self.to_]),
                LogLine([self.unit, "fails to move"]),
            ):
                return None


@dataclasses.dataclass
class SpawnUnit(Event[Unit | None]):
    blueprint: UnitBlueprint
    controller: Player
    space: Hex
    exhausted: bool = False
    with_statuses: Iterable[UnitStatusSignature] = ()
    max_health: int | None = None
    max_energy: int | None = None

    def is_valid(self) -> bool:
        return not self.space.map.unit_on(self.space)

    def resolve(self) -> Unit | None:
        unit = Unit(self.controller, self.blueprint, exhausted=self.exhausted)
        if not self.space.map.move_unit_to(unit, self.space):
            return None
        if self.max_health and unit.health > self.max_health:
            unit.damage = unit.health - self.max_health
        if self.max_energy and unit.energy > self.max_energy:
            unit.energy = self.max_energy
        GS.update_vision()
        with GS.log(LogLine([unit, "is spawned in", self.space])):
            for signature in self.with_statuses:
                unit.add_status(signature)
        return unit


# TODO currently only used in effects. Should prob be used everywhere.
#  Requires refactoring movement cost.
@dataclasses.dataclass
class ModifyMovementPoints(Event[None]):
    unit: Unit
    amount: int

    def is_valid(self) -> bool:
        return (
            self.amount
            and GS.active_unit_context
            and GS.active_unit_context.unit == self.unit
        )

    def resolve(self) -> None:
        # TODO log ?
        GS.active_unit_context.movement_points += self.amount


@dataclasses.dataclass
class ExhaustUnit(Event[None]):
    unit: Unit

    def is_valid(self) -> bool:
        return not self.unit.exhausted

    def resolve(self) -> None:
        # TODO shouldn't log when exhausted through normal action?
        with GS.log(LogLine([self.unit, "is exhausted"])):
            self.unit.exhausted = True


@dataclasses.dataclass
class ReadyUnit(Event[None]):
    unit: Unit

    def is_valid(self) -> bool:
        return self.unit.exhausted

    def resolve(self) -> None:
        # TODO log? but not if normal beginning of round?
        self.unit.exhausted = False


@dataclasses.dataclass
class MovePenalty(Event[None]):
    unit: Unit
    hex: Hex
    amount: int
    in_: bool

    def is_valid(self) -> bool:
        return self.amount > 0

    def resolve(self) -> None:
        # TODO log ?
        GS.active_unit_context.movement_points -= self.amount


@dataclasses.dataclass
class MoveAction(Event[None]):
    unit: Unit
    to_: Hex

    def resolve(self) -> None:
        _from = GS.map.hex_off(self.unit)
        movement_cost = self.to_.get_move_in_cost_for(self.unit)
        move_out_penalty = MovePenalty(
            self.unit, _from, _from.get_move_out_penalty_for(self.unit), False
        )
        move_in_penalty = MovePenalty(
            self.unit, self.to_, self.to_.get_move_in_penalty_for(self.unit), True
        )
        ES.resolve(self.branch(MoveUnit))
        # TODO event only valid if context is not null?
        GS.active_unit_context.movement_points -= movement_cost
        ES.resolve(move_out_penalty)
        ES.resolve(move_in_penalty)


@dataclasses.dataclass
class Rest(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        with GS.log(LogLine([self.unit, "rests"])):
            GS.active_unit_context.should_stop = True


# TODO where should this be?
# TODO currently only checked in turn, should prob be checked in round as well.
def do_state_based_check() -> None:
    has_changed = True
    while has_changed:
        has_changed = ES.resolve_pending_triggers()
        # TODO order?
        for unit in list(GS.map.unit_positions.keys()):
            if unit.health <= 0 or not GS.map.hex_off(unit).is_passable_to(unit):
                has_changed = True
                ES.resolve(Kill(unit))


@dataclasses.dataclass
class QueueUnitForActivation(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        # TODO log ?
        GS.activation_queued_units.add(self.unit)


# TODO IDK
@dataclasses.dataclass()
class TurnUpkeep(Event[None]):
    unit: Unit

    def resolve(self) -> None: ...


# TODO IDK
@dataclasses.dataclass()
class TurnCleanup(Event[None]):
    unit: Unit

    def resolve(self) -> None: ...


# TODO IDK
@dataclasses.dataclass()
class ActionUpkeep(Event[None]):
    unit: Unit

    def resolve(self) -> None: ...


# TODO IDK
@dataclasses.dataclass()
class ActionCleanup(Event[None]):
    unit: Unit

    def resolve(self) -> None: ...


@dataclasses.dataclass
class Turn(Event[bool]):
    unit: Unit

    def resolve(self) -> bool:
        GS.active_unit_context = context = ActiveUnitContext(
            self.unit, max(self.unit.speed.g(), 0)
        )

        # TODO this prob shouldn't be here. For now it is to make sure we have a
        #  vision map when unit tests run just a turn.
        GS.update_vision()

        with GS.log(LogLine([self.unit, "is activated"])):
            ES.resolve(TurnUpkeep(unit=self.unit))
            do_state_based_check()

            while not context.should_stop and self.unit.on_map():
                if not (
                    legal_options := [
                        option
                        for option in self.unit.get_legal_options(context)
                        if context.locked_into is None
                        or isinstance(option, SkipOption)
                        or (
                            isinstance(option, EffortOption)
                            and option.facet == context.locked_into
                        )
                    ]
                ):
                    break

                ES.resolve(ActionUpkeep(unit=self.unit))

                # TODO maybe have some is_auto_resolvable thing instead?
                if all(isinstance(option, SkipOption) for option in legal_options):
                    decision = OptionDecision(legal_options[0], None)
                else:
                    decision = GS.make_decision(
                        self.unit.controller,
                        SelectOptionDecisionPoint(legal_options, explanation="do shit"),
                    )

                if isinstance(decision.option, SkipOption):
                    # TODO difference here is whether or not it is a "TurnSkip" or an "end actions skip"
                    if context.has_acted:
                        GS.active_unit_context.should_stop = True
                    else:
                        ES.resolve(Rest(self.unit))
                    break

                elif isinstance(decision.option, MoveOption):
                    ES.resolve(MoveAction(self.unit, to_=decision.target))

                elif isinstance(decision.option, EffortOption):
                    context.activated_facets[
                        decision.option.facet.__class__.__name__
                    ] += 1
                    if isinstance(decision.option.facet, MeleeAttackFacet):
                        ES.resolve(
                            MeleeAttackAction(
                                attacker=self.unit,
                                defender=decision.target,
                                attack=decision.option.facet,
                            )
                        )
                    elif isinstance(decision.option.facet, RangedAttackFacet):
                        ES.resolve(
                            RangedAttackAction(
                                attacker=self.unit,
                                defender=decision.target,
                                attack=decision.option.facet,
                            )
                        )
                    elif isinstance(decision.option.facet, ActivatedAbilityFacet):
                        ES.resolve(
                            ActivateAbilityAction(
                                unit=self.unit,
                                ability=decision.option.facet,
                                target=decision.target,
                            )
                        )

                    else:
                        raise ValueError("blah")
                    # TODO unclear which of this logic should be on the action event, and which should be here...
                    if not decision.option.facet.combinable:
                        if decision.option.facet.max_activations != 1:
                            context.locked_into = decision.option.facet
                        else:
                            context.should_stop = True
                else:
                    raise ValueError("blah")

                # TODO yikes. need this right now for juke and jive, not sure what the plan is.
                GS.update_vision()
                ES.resolve(ActionCleanup(unit=self.unit))
                do_state_based_check()
                context.has_acted = True

            GS.update_ghosts()
            ES.resolve(TurnCleanup(unit=self.unit))
            do_state_based_check()

            ES.resolve(ExhaustUnit(self.unit))
            GS.active_unit_context = None

        return context.has_acted


class RoundUpkeep(Event[None]):
    def resolve(self) -> None:
        for unit in list(GS.map.unit_positions.keys()):
            ES.resolve(GainEnergy(unit, unit.energy_regen.g(), source=None))
            for status in list(unit.statuses):
                status.decrement_duration()
        for hex_ in GS.map.hexes.values():
            for status in list(hex_.statuses):
                status.decrement_duration()


@dataclasses.dataclass
class GainPoints(Event[None]):
    player: Player
    amount: int

    def is_valid(self) -> bool:
        return self.amount > 0

    def resolve(self) -> None:
        with GS.log(LogLine([self.player, f"gains {self.amount} points"])):
            self.player.points += self.amount


class AwardPoints(Event[None]):
    def resolve(self) -> None:
        for unit, _hex in GS.map.unit_positions.items():
            if _hex.is_objective and unit.can_capture_objectives_on(_hex):
                _hex.captured_by = unit.controller

        player_values: dict[Player, int] = defaultdict(int)
        for _hex in GS.map.hexes.values():
            if _hex.captured_by:
                player_values[_hex.captured_by] += 1

        for player, amount in player_values.items():
            ES.resolve(GainPoints(player, amount))


class RoundCleanup(Event[None]):
    def resolve(self) -> None:
        ES.resolve(AwardPoints())


class Round(Event[None]):
    def resolve(self) -> None:
        gs = GS
        gs.round_counter += 1
        skipped_players: set[Player] = set()
        waiting_players: set[Player] = set()
        all_players = set(gs.turn_order)
        last_action_timestamps: dict[Player, int] = {
            player: 0 for player in gs.turn_order
        }
        timestamp = 0

        for unit in gs.map.unit_positions.keys():
            ES.resolve(ReadyUnit(unit))

        with gs.log(LogLine([f"Round {gs.round_counter}"])):
            # TODO very unclear how this all works
            ES.resolve(RoundUpkeep())
            do_state_based_check()

            while skipped_players != all_players:
                timestamp += 1
                player = gs.turn_order.active_player

                GS.update_vision()

                # TODO blah and tests
                activateable_units = None
                if gs.activation_queued_units:
                    if activateable_queued_units := [
                        unit
                        for unit in gs.activation_queued_units
                        if unit.can_be_activated(None)
                    ]:
                        queued_turn_order = TurnOrder(gs.turn_order.all_players)
                        # TODO wtf is happening here?
                        while not (
                            activateable_units := [
                                unit
                                for unit in activateable_queued_units
                                if unit.controller == player
                            ]
                        ):
                            player = queued_turn_order.advance()

                    else:
                        gs.activation_queued_units.clear()

                if activateable_units is None:
                    gs.turn_order.advance()
                    activateable_units = [
                        unit
                        for unit in gs.map.units_controlled_by(player)
                        if unit.can_be_activated(None)
                    ]

                if not activateable_units:
                    skipped_players.add(player)
                    continue

                skipped_players.discard(player)

                action_previews = {
                    unit: unit.get_legal_options(ActiveUnitContext(unit, 1))
                    for unit in activateable_units
                }

                decision = GS.make_decision(
                    player,
                    SelectOptionDecisionPoint(
                        [
                            ActivateUnitOption(
                                target_profile=OneOfUnits(activateable_units),
                                actions_previews=action_previews,
                            ),
                            *(
                                ()
                                if gs.activation_queued_units
                                or not all(
                                    any(
                                        isinstance(option, SkipOption)
                                        for option in options
                                    )
                                    for options in action_previews.values()
                                )
                                else (SkipOption(target_profile=NoTarget()),)
                            ),
                        ],
                        explanation="activate unit?",
                    ),
                )
                if isinstance(decision.option, ActivateUnitOption):
                    waiting_players = set()

                    if gs.activation_queued_units:
                        gs.activation_queued_units.discard(decision.target)

                    if any(
                        turn.result
                        for turn in ES.resolve(Turn(decision.target)).iter_type(Turn)
                    ):
                        last_action_timestamps[player] = timestamp
                    do_state_based_check()

                elif isinstance(decision.option, SkipOption):
                    with gs.log(LogLine([player, "waits"])):
                        skipped_players.add(player)
                        waiting_players.add(player)

            # TODO should we trigger turn skip for remaining units or something?

            with gs.log(LogLine(["Round cleanup"])):
                ES.resolve(RoundCleanup())
                do_state_based_check()

            gs.turn_order.set_player_order(
                sorted(gs.turn_order, key=lambda p: last_action_timestamps[p])
            )


@dataclasses.dataclass
class DeployArmies(Event[None]):
    landscape: Landscape

    def resolve(self) -> None:
        GS.update_vision()
        for player, deployment in GS.make_parallel_decision(
            {
                player: DeployArmyDecisionPoint(
                    12,
                    70,
                    [
                        GS.map.hexes[cc]
                        for cc, spec in self.landscape.terrain_map.items()
                        if spec.deployment_zone_of == idx
                    ],
                )
                for idx, player in enumerate(reversed(GS.turn_order.original_order))
            }
        ).items():
            for blueprint, hex_ in deployment:
                ES.resolve(SpawnUnit(blueprint, player, hex_))


@dataclasses.dataclass
class Play(Event[None]):
    def resolve(self) -> None:
        gs = GS
        while (
            not (
                any(p.points >= gs.target_points for p in gs.turn_order)
                and len({p.points for p in gs.turn_order}) != 1
            )
            and gs.round_counter < 10
        ):
            ES.resolve(Round())

        winner = max(
            gs.turn_order,
            key=lambda p: (p.points, p == gs.turn_order.original_order[0]),
        )
        with gs.log(LogLine([winner.name, "wins"])):
            pass
        gs.send_to_players()
