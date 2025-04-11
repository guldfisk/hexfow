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
)
from game.game.decision_points import SelectUnitDecisionPoint
from game.game.decisions import OptionDecision, SelectOptionDecisionPoint
from game.game.player import Player
from game.game.select import select_unit, select_targeted_option
from game.game.units.facets.attacks import MeleeAttackFacet


@dataclasses.dataclass
class Damage(Event[None]):
    unit: Unit
    amount: int

    def resolve(self) -> None:
        self.unit.damage += self.amount


@dataclasses.dataclass
class MeleeAttack(Event[None]):
    attacker: Unit
    defender: Unit
    attack: MeleeAttackFacet

    def resolve(self) -> None:
        ES.resolve(Damage(self.defender, self.attack.damage))
        # self.defender.health -= self.attack.damage


@dataclasses.dataclass
class Kill(Event[None]):
    unit: Unit

    def resolve(self) -> None:
        GS().map.remove_unit(self.unit)


@dataclasses.dataclass
class CheckAlive(Event[bool]):
    unit: Unit

    def resolve(self) -> bool:
        if self.unit.health <= 0:
            ES.resolve(Kill(self.unit))
            return False
        return True


@dataclasses.dataclass
class MeleeAttackAction(Event[None]):
    attacker: Unit
    defender: Unit
    attack: MeleeAttackFacet

    def resolve(self) -> None:
        defender_position = GS().map.unit_positions[self.defender]
        ES.resolve(self.branch(MeleeAttack))
        ES.resolve(CheckAlive(self.defender))
        if defender_position.can_move_into(self.attacker):
            ES.resolve(MoveUnit(self.attacker, defender_position))
        GS().active_unit_context.movement_points -= 1


@dataclasses.dataclass
class MoveUnit(Event[Hex | None]):
    unit: Unit
    to_: Hex

    def resolve(self) -> Hex | None:
        if not self.to_.can_move_into(self.unit):
            return None
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
class MoveAction(Event[None]):
    unit: Unit
    to_: Hex

    def resolve(self) -> None:
        ES.resolve(self.branch(MoveUnit))
        GS().active_unit_context.movement_points -= 1


@dataclasses.dataclass
class Turn(Event[bool]):
    # player: Player
    unit: Unit

    def resolve(self) -> bool:
        # activateable_units = [
        #     unit
        #     for unit in GS().map.units_controlled_by(self.player)
        #     if unit.can_be_activated()
        # ]
        # if not activateable_units:
        #     return False
        #
        # # selected_unit = GS().take_action()
        # selected_unit = select_unit(activateable_units)
        # context =
        GS().active_unit_context = context = ActiveUnitContext(
            self.unit, self.unit.speed.g()
        )

        while not context.should_stop and (
            legal_options := self.unit.get_legal_options(context)
        ):
            decision = GS().make_decision(
                self.unit.controller,
                SelectOptionDecisionPoint(legal_options, explanation="do shit"),
            )
            # option, target = select_targeted_option(legal_options)
            if isinstance(decision.option, SkipOption):
                ES.resolve_pending_triggers()
                break
            elif isinstance(decision.option, MoveOption):
                ES.resolve(MoveAction(self.unit, to_=decision.target))
            elif isinstance(decision.option, EffortOption):
                if isinstance(decision.option.facet, MeleeAttackFacet):
                    ES.resolve(
                        MeleeAttackAction(
                            attacker=self.unit,
                            defender=decision.target,
                            attack=decision.option.facet,
                        )
                    )
                else:
                    raise ValueError("blah")
            else:
                raise ValueError("blah")
            ES.resolve_pending_triggers()
            context.has_acted = True

        self.unit.exhausted = True
        GS().active_unit_context = None

        return context.has_acted


class Round(Event[None]):

    def resolve(self) -> None:
        gs = GS()
        gs.round_counter += 1
        skipped_players: set[Player] = set()
        all_players = set(gs.turn_order.players)
        last_action_timestamps: dict[Player, int] = {
            player: 0 for player in gs.turn_order.players
        }
        timestamp = 0

        for unit in gs.map.unit_positions.keys():
            unit.exhausted = False

        while skipped_players != all_players:
            timestamp += 1
            player = gs.turn_order.advance()
            activateable_units = [
                unit
                for unit in gs.map.units_controlled_by(player)
                if unit.can_be_activated(None)
            ]
            if not activateable_units:
                skipped_players.add(player)
                continue
            skipped_players.discard(player)

            if any(
                turn.result
                for turn in ES.resolve(
                    Turn(
                        gs.make_decision(
                            player,
                            SelectUnitDecisionPoint(
                                activateable_units, "activate unit"
                            ),
                        )
                    )
                ).iter_type(Turn)
            ):
                last_action_timestamps[player] = timestamp

        gs.turn_order.set_player_order(
            sorted(gs.turn_order.players, key=lambda p: last_action_timestamps[p])
        )


@dataclasses.dataclass
class Play(Event[None]):

    def resolve(self) -> None:
        gs = GS()
        while (
            not any(p.points >= gs.target_points for p in gs.turn_order.players)
            and gs.round_counter < 20
        ):
            ES.resolve(Round())
