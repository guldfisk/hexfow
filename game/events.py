import dataclasses
import math
from typing import Iterable

from events.eventsystem import Event, ES, V
from game.core import (
    Unit,
    Hex,
    UnitBlueprint,
    GS,
    ActiveUnitContext,
    MoveOption,
    EffortOption,
    SkipOption,
    RangedAttackFacet,
    ActivateUnitOption,
    OneOfUnits,
    TerrainProtectionRequest,
    MeleeAttackFacet,
    SingleTargetAttackFacet,
    ActivatedAbilityFacet,
    StatusSignature,
    HexStatusSignature,
    DamageSignature,
)
from game.decisions import SelectOptionDecisionPoint, NoTarget, O, OptionDecision
from game.player import Player
from game.values import DamageType, StatusIntention, Resistance


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
        ES.resolve(self.branch(KillUpkeep))
        GS().map.remove_unit(self.unit)
        self.unit.deregister()


# TODO don't think this should be an event?
@dataclasses.dataclass
class CheckAlive(Event[bool]):
    unit: Unit

    def resolve(self) -> bool:
        # TODO common logic
        if self.unit.health <= 0 or not GS().map.hex_off(self.unit).is_passable_to(
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
        return self.amount > 0

    def resolve(self) -> int:
        heal_amount = min(self.amount, self.unit.damage)
        self.unit.damage -= heal_amount
        return heal_amount


@dataclasses.dataclass
class GainEnergy(Event[int]):
    unit: Unit
    amount: int

    def is_valid(self) -> bool:
        return self.amount > 0 and self.unit.energy < self.unit.max_energy.g()

    def resolve(self) -> int:
        amount = max(min(self.amount, self.unit.max_energy.g() - self.unit.energy), 0)
        self.unit.energy += amount
        return amount


@dataclasses.dataclass
class SufferDamage(Event[int]):
    unit: Unit
    signature: DamageSignature

    def is_valid(self) -> bool:
        return self.signature.amount > 0

    def resolve(self) -> int:
        return self.unit.suffer_damage(self.signature)


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
                - self.unit.get_terrain_protection_for(
                    TerrainProtectionRequest(self.unit, self.signature.type)
                ),
                min(self.signature.amount, 1),
            )
        )
        ES.resolve(ReceiveDamage(self.unit, self.signature.with_damage(damage)))
        return damage


@dataclasses.dataclass
class SimpleAttack(Event[None]):
    attacker: Unit
    defender: Unit
    attack: SingleTargetAttackFacet

    def resolve(self) -> None:
        # TODO some way to formalize this?
        if not self.attacker.on_map() or not self.defender.on_map():
            return
        self.attack.resolve_pre_damage_effects(self.defender)
        ES.resolve(
            Damage(
                self.defender, self.attack.get_damage_signature_against(self.defender)
            )
        )
        # TODO do we actually want this here, or should it be triggers?
        self.attack.resolve_post_damage_effects(self.defender)


@dataclasses.dataclass
class MeleeAttackAction(Event[None]):
    attacker: Unit
    defender: Unit
    attack: MeleeAttackFacet

    def resolve(self) -> None:
        defender_position = GS().map.hex_off(self.defender)
        attacker_position = GS().map.hex_off(self.attacker)
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
        ES.resolve(self.branch(SimpleAttack))
        ES.resolve(CheckAlive(self.defender))
        if defender_position.can_move_into(self.attacker):
            ES.resolve(MoveUnit(self.attacker, defender_position))
        self.attack.get_cost().pay(GS().active_unit_context)
        ES.resolve(move_out_penalty)
        ES.resolve(move_in_penalty)
        # GS().active_unit_context.should_stop = True


@dataclasses.dataclass
class RangedAttackAction(Event[None]):
    attacker: Unit
    defender: Unit
    attack: RangedAttackFacet

    def resolve(self) -> None:
        ES.resolve(self.branch(SimpleAttack))
        ES.resolve(CheckAlive(self.defender))
        self.attack.get_cost().pay(GS().active_unit_context)


# TODO where?
def apply_status_to_unit(
    unit: Unit, signature: StatusSignature, by: Player | None
) -> None:
    unit.add_status(
        signature.status_type(
            intention=signature.intention
            or signature.status_type.default_intention
            or (
                (
                    StatusIntention.BUFF
                    if unit.controller == by
                    else StatusIntention.DEBUFF
                )
                if by
                else StatusIntention.NEUTRAL
            ),
            duration=signature.duration,
            stacks=signature.stacks,
            parent=unit,
        ),
        by,
    )


@dataclasses.dataclass
class ApplyStatus(Event[None]):
    unit: Unit
    by: Player | None
    signature: StatusSignature

    def is_valid(self) -> bool:
        return self.unit.on_map()

    def resolve(self) -> None:
        apply_status_to_unit(self.unit, self.signature, self.by)


@dataclasses.dataclass
class ApplyHexStatus(Event[None]):
    space: Hex
    by: Player | None
    signature: HexStatusSignature

    def resolve(self) -> None:
        self.space.add_status(
            self.signature.status_type(
                duration=self.signature.duration,
                stacks=self.signature.stacks,
                parent=self.space,
            ),
            self.by,
        )


@dataclasses.dataclass
class ActivatedAbilityAction(Event[None]):
    unit: Unit
    ability: ActivatedAbilityFacet[O]
    target: O

    def resolve(self) -> None:
        self.ability.perform(self.target)
        self.ability.get_cost().pay(GS().active_unit_context)


@dataclasses.dataclass
class MoveUnit(Event[Hex | None]):
    unit: Unit
    to_: Hex

    def is_valid(self) -> bool:
        return self.to_.can_move_into(self.unit)

    def resolve(self) -> Hex | None:
        from_ = self.to_.map.hex_off(self.unit)
        self.to_.map.move_unit_to(self.unit, self.to_)
        return from_


@dataclasses.dataclass
class SpawnUnit(Event[Unit | None]):
    blueprint: UnitBlueprint
    controller: Player
    space: Hex
    exhausted: bool = False
    with_statuses: Iterable[StatusSignature] = ()

    def is_valid(self) -> bool:
        return not self.space.map.unit_on(self.space)

    def resolve(self) -> Unit | None:
        unit = Unit(self.controller, self.blueprint, exhausted=self.exhausted)
        self.space.map.move_unit_to(unit, self.space)
        for signature in self.with_statuses:
            apply_status_to_unit(unit, signature, self.controller)
        return unit


@dataclasses.dataclass
class MovePenalty(Event[None]):
    unit: Unit
    hex: Hex
    amount: int
    in_: bool

    def resolve(self) -> None:
        GS().active_unit_context.movement_points -= self.amount


@dataclasses.dataclass
class MoveAction(Event[None]):
    unit: Unit
    to_: Hex

    def resolve(self) -> None:
        _from = GS().map.hex_off(self.unit)
        move_out_penalty = MovePenalty(
            self.unit, _from, _from.get_move_out_penalty_for(self.unit), False
        )
        move_in_penalty = MovePenalty(
            self.unit, self.to_, self.to_.get_move_in_penalty_for(self.unit), True
        )
        ES.resolve(self.branch(MoveUnit))
        # TODO event only valid if context is not null?
        GS().active_unit_context.movement_points -= 1
        ES.resolve(move_out_penalty)
        ES.resolve(move_in_penalty)


@dataclasses.dataclass
class Rest(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        GS().active_unit_context.should_stop = True


# TODO where should this be?
# TODO currently only checked in turn, should prob be checked in round as well.
def do_state_based_check() -> None:
    has_changed = True
    while has_changed:
        has_changed = ES.resolve_pending_triggers()
        # TODO order?
        for unit in list(GS().map.unit_positions.keys()):
            if unit.health <= 0 or not GS().map.hex_off(unit).is_passable_to(unit):
                has_changed = True
                ES.resolve(Kill(unit))


@dataclasses.dataclass
class QueueUnitForActivation(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        GS().activation_queued_units.add(self.unit)


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


@dataclasses.dataclass
class Turn(Event[bool]):
    unit: Unit

    def resolve(self) -> bool:
        GS().active_unit_context = context = ActiveUnitContext(
            self.unit, self.unit.speed.g()
        )

        ES.resolve(TurnUpkeep(unit=self.unit))
        do_state_based_check()

        while not context.should_stop and self.unit.on_map():
            # TODO this prob shouldn't be here. For now it is to make sure we have a
            #  vision map when unit tests run just a turn.
            GS().update_vision()

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
                decision = GS().make_decision(
                    self.unit.controller,
                    SelectOptionDecisionPoint(legal_options, explanation="do shit"),
                )

            if isinstance(decision.option, SkipOption):
                # TODO difference here is whether or not it is a "TurnSkip" or an "end actions skip"
                if context.has_acted:
                    GS().active_unit_context.should_stop = True
                else:
                    ES.resolve(Rest(self.unit))
                do_state_based_check()
                break
            elif isinstance(decision.option, MoveOption):
                ES.resolve(MoveAction(self.unit, to_=decision.target))
            elif isinstance(decision.option, EffortOption):
                context.activated_facets[decision.option.facet.__class__.__name__] += 1
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
                        ActivatedAbilityAction(
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

            do_state_based_check()
            context.has_acted = True

        ES.resolve(TurnCleanup(unit=self.unit))
        do_state_based_check()

        self.unit.exhausted = True
        GS().active_unit_context = None

        return context.has_acted


class RoundUpkeep(Event[None]):
    def resolve(self) -> None:
        for unit in list(GS().map.unit_positions.keys()):
            ES.resolve(GainEnergy(unit, unit.energy_regen.g()))
            for status in list(unit.statuses):
                status.decrement_duration()
        for hex_ in GS().map.hexes.values():
            for status in list(hex_.statuses):
                status.decrement_duration()


class RoundCleanup(Event[None]):
    def resolve(self) -> None:
        return None


class Round(Event[None]):
    def resolve(self) -> None:
        gs = GS()
        gs.round_counter += 1
        skipped_players: set[Player] = set()
        # TODO asker's shit
        round_skipped_players: set[Player] = set()
        all_players = set(gs.turn_order.players)
        last_action_timestamps: dict[Player, int] = {
            player: 0 for player in gs.turn_order.players
        }
        timestamp = 0

        for unit in gs.map.unit_positions.keys():
            unit.exhausted = False

        # TODO very unclear how this all works
        ES.resolve(RoundUpkeep())
        do_state_based_check()

        while skipped_players != all_players:
            timestamp += 1
            player = gs.turn_order.active_player
            gs.turn_order.advance()
            if player in round_skipped_players:
                continue

            GS().update_vision()

            # TODO blah and tests
            activateable_units = None
            if gs.activation_queued_units:
                if activateable_queued_units := [
                    unit
                    for unit in gs.activation_queued_units
                    if unit.can_be_activated(None)
                ]:
                    while not (
                        activateable_units := [
                            unit
                            for unit in activateable_queued_units
                            if unit.controller == player
                        ]
                    ):
                        player = gs.turn_order.advance()

                else:
                    gs.activation_queued_units.clear()
            if activateable_units is None:
                activateable_units = [
                    unit
                    for unit in gs.map.units_controlled_by(player)
                    if unit.can_be_activated(None)
                ]
            if not activateable_units:
                skipped_players.add(player)
                continue
            skipped_players.discard(player)

            decision = GS().make_decision(
                player,
                SelectOptionDecisionPoint(
                    [
                        ActivateUnitOption(
                            target_profile=OneOfUnits(activateable_units)
                        ),
                        *(
                            ()
                            if gs.activation_queued_units
                            or not all(
                                any(
                                    isinstance(option, SkipOption)
                                    for option in unit.get_legal_options(
                                        # TODO, this is pretty ugly, but it sorta makes sense.
                                        ActiveUnitContext(unit, -1)
                                    )
                                )
                                for unit in activateable_units
                            )
                            else (SkipOption(target_profile=NoTarget()),)
                        ),
                    ],
                    explanation="activate unit?",
                ),
            )
            if isinstance(decision.option, ActivateUnitOption):
                if gs.activation_queued_units:
                    gs.activation_queued_units.discard(decision.target)
                if any(
                    turn.result
                    for turn in ES.resolve(Turn(decision.target)).iter_type(Turn)
                ):
                    last_action_timestamps[player] = timestamp
            elif isinstance(decision.option, SkipOption):
                skipped_players.add(player)
                round_skipped_players.add(player)
            else:
                raise ValueError("AHLO")

        # TODO should we trigger turn skip for remaining units or something?

        ES.resolve(RoundCleanup())
        do_state_based_check()

        gs.turn_order.set_player_order(
            sorted(gs.turn_order.players, key=lambda p: last_action_timestamps[p])
        )


@dataclasses.dataclass
class Play(Event[None]):
    def resolve(self) -> None:
        gs = GS()
        first_player = gs.turn_order.players[0]
        while (
            not (
                any(p.points >= gs.target_points for p in gs.turn_order.players)
                and len({p.points for p in gs.turn_order.players}) != 1
            )
            # TODO do want something like this prob, annoying when testing
            # and gs.round_counter < 20
        ):
            print(
                any(p.points >= gs.target_points for p in gs.turn_order.players),
                len({p.points for p in gs.turn_order.players}) == 1,
            )
            ES.resolve(Round())
            # for unit, _hex in gs.map.unit_positions.items():
            #     if _hex.is_objective:
            #         unit.controller.points += 1

        winner = max(gs.turn_order.players, key=lambda p: (p.points, p == first_player))
        print("WINNER: ", winner)

        # TODO push last game state and result to clients
