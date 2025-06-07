import dataclasses

from events.eventsystem import Event, ES, V
from game.game.core import (
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
    UnitStatus,
    StatusType,
)
from game.game.damage import DamageSignature
from game.game.decisions import SelectOptionDecisionPoint, NoTarget, O
from game.game.player import Player
from game.game.values import DamageType


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
        if self.unit.health <= 0 or not GS().map.position_of(self.unit).is_passable_to(
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
        return self.amount > 0

    def resolve(self) -> int:
        amount = max(min(self.amount, self.unit.max_energy.g() - self.unit.energy), 0)
        self.unit.energy += amount
        return amount


@dataclasses.dataclass
class Damage(Event[int]):
    unit: Unit
    signature: DamageSignature

    def is_valid(self) -> bool:
        return self.signature.amount > 0

    def resolve(self) -> int:
        defender_armor = self.unit.armor.g()
        damage = (
            self.signature.amount
            if self.signature.type == DamageType.TRUE
            else max(
                self.signature.amount
                - min(defender_armor, max(defender_armor - self.signature.ap, 0)),
                0,
            )
        )
        self.unit.damage += damage
        return damage


# TODO idk where
def get_terrain_modified_damage(
    # amount: int, defender: Unit, damage_type: DamageType
    damage_signature: DamageSignature,
    defender: Unit,
) -> DamageSignature:
    return DamageSignature(
        max(
            damage_signature.amount
            - GS()
            .map.position_of(defender)
            .get_terrain_protection_for(
                TerrainProtectionRequest(defender, damage_signature.type)
            ),
            min(damage_signature.amount, 1),
        ),
        type=damage_signature.type,
        ap=damage_signature.ap,
    )


@dataclasses.dataclass
class SimpleAttack(Event[None]):
    attacker: Unit
    defender: Unit
    attack: SingleTargetAttackFacet

    def resolve(self) -> None:
        # TODO some way to formalize this?
        if not self.attacker.on_map() or not self.defender.on_map():
            return
        ES.resolve(
            Damage(
                self.defender,
                get_terrain_modified_damage(
                    self.attack.get_damage_signature_against(self.defender),
                    self.defender,
                ),
            )
        )


@dataclasses.dataclass
class MeleeAttackAction(Event[None]):
    attacker: Unit
    defender: Unit
    attack: MeleeAttackFacet

    def resolve(self) -> None:
        defender_position = GS().map.position_of(self.defender)
        attacker_position = GS().map.position_of(self.attacker)
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
        # TODO movement cost of attack?
        GS().active_unit_context.movement_points -= 1 + self.attack.movement_cost
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
        GS().active_unit_context.movement_points -= self.attack.movement_cost
        # GS().active_unit_context.should_stop = True


@dataclasses.dataclass
class ApplyStatus(Event[None]):
    unit: Unit
    status_type: type[UnitStatus]
    by: Player | None
    stacks: int | None = None
    duration: int | None = None

    def resolve(self) -> None:
        self.unit.add_status(
            # TODO clean up status inheritance, make that shit not dataclasses i think
            self.status_type(
                type_=(
                    (
                        StatusType.BUFF
                        if self.unit.controller == self.by
                        else StatusType.DEBUFF
                    )
                    if self.by
                    else StatusType.NEUTRAL
                ),
                duration=self.duration,
                original_duration=self.duration,
                stacks=self.stacks,
                parent=self.unit,
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
        GS().active_unit_context.movement_points -= self.ability.movement_cost
        self.unit.energy -= self.ability.energy_cost


@dataclasses.dataclass
class MoveUnit(Event[Hex | None]):
    unit: Unit
    to_: Hex

    def is_valid(self) -> bool:
        return self.to_.can_move_into(self.unit)

    def resolve(self) -> Hex | None:
        from_ = self.to_.map.position_of(self.unit)
        self.to_.map.move_unit_to(self.unit, self.to_)
        return from_


@dataclasses.dataclass
class SpawnUnit(Event[Unit | None]):
    blueprint: UnitBlueprint
    controller: Player
    space: Hex
    exhausted: bool = False

    def resolve(self) -> Unit | None:
        if self.space.map.unit_on(self.space):
            return None
        unit = Unit(self.controller, self.blueprint, exhausted=self.exhausted)
        self.space.map.move_unit_to(unit, self.space)
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
        _from = GS().map.position_of(self.unit)
        move_out_penalty = MovePenalty(
            self.unit, _from, _from.get_move_out_penalty_for(self.unit), False
        )
        move_in_penalty = MovePenalty(
            self.unit, self.to_, self.to_.get_move_in_penalty_for(self.unit), True
        )
        ES.resolve(self.branch(MoveUnit))
        GS().active_unit_context.movement_points -= 1
        ES.resolve(move_out_penalty)
        ES.resolve(move_in_penalty)


@dataclasses.dataclass
class SkipAction(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        GS().active_unit_context.should_stop = True


# TODO where should this be?
# TODO currently only checed in turn, should prob be checked in round as well.
def do_state_based_check() -> None:
    has_changed = True
    while has_changed:
        has_changed = ES.resolve_pending_triggers()
        # TODO order?
        for unit in list(GS().map.unit_positions.keys()):
            if unit.health <= 0 or not GS().map.position_of(unit).is_passable_to(unit):
                has_changed = True
                ES.resolve(Kill(unit))


# TODO IDK
@dataclasses.dataclass()
class TurnUpkeep(Event[None]):
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

            if not (legal_options := self.unit.get_legal_options(context)):
                break

            decision = GS().make_decision(
                self.unit.controller,
                SelectOptionDecisionPoint(legal_options, explanation="do shit"),
            )
            if isinstance(decision.option, SkipOption):
                ES.resolve(SkipAction(self.unit))
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
                    context.should_stop = True
            else:
                raise ValueError("blah")

            do_state_based_check()
            context.has_acted = True

        self.unit.exhausted = True
        GS().active_unit_context = None

        return context.has_acted


class Upkeep(Event[None]):
    def resolve(self) -> None:
        for unit in GS().map.unit_positions.keys():
            if unit.energy < unit.max_energy.g():
                ES.resolve(GainEnergy(unit, 1))
            for status in list(unit.statuses):
                status.decrement_duration()


class Round(Event[None]):
    def resolve(self) -> None:
        gs = GS()
        gs.round_counter += 1
        skipped_players: set[Player] = set()
        round_skipped_players: set[Player] = set()
        all_players = set(gs.turn_order.players)
        last_action_timestamps: dict[Player, int] = {
            player: 0 for player in gs.turn_order.players
        }
        timestamp = 0

        for unit in gs.map.unit_positions.keys():
            unit.exhausted = False

        # TODO very unclear how this all works
        ES.resolve(Upkeep())
        do_state_based_check()

        while skipped_players != all_players:
            timestamp += 1
            player = gs.turn_order.active_player
            gs.turn_order.advance()
            if player in round_skipped_players:
                continue

            GS().update_vision()

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
                        SkipOption(target_profile=NoTarget()),
                    ],
                    explanation="activate unit?",
                ),
            )
            if isinstance(decision.option, ActivateUnitOption):
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

        gs.turn_order.set_player_order(
            sorted(gs.turn_order.players, key=lambda p: last_action_timestamps[p])
        )


@dataclasses.dataclass
class Play(Event[None]):
    def resolve(self) -> None:
        gs = GS()
        while (
            not any(p.points >= gs.target_points for p in gs.turn_order.players)
            # TODO do want something like this prob, annoying when testing
            # and gs.round_counter < 20
        ):
            ES.resolve(Round())
        # TODO push last game state and result to clients
