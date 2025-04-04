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
)
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
        context = ActiveUnitContext(self.unit, self.unit.speed.g())
        GS().active_unit_context = context

        while not context.should_stop and (
            legal_options := self.unit.get_legal_options()
        ):
            option, target = select_targeted_option(legal_options)
            if isinstance(option, MoveOption):
                ES.resolve(MoveAction(self.unit, to_=target))
            elif isinstance(option, EffortOption):
                if isinstance(option.facet, MeleeAttackFacet):
                    ES.resolve(
                        MeleeAttack(
                            attacker=self.unit, defender=target, attack=option.facet
                        )
                    )
                else:
                    raise ValueError("blah")
            else:
                raise ValueError("blah")
            ES.resolve_pending_triggers()

        self.unit.exhausted = True
        GS().active_unit_context = None

        return True


class Round(Event[None]):

    def resolve(self) -> None:
        gs = GS()
        gs.round_counter += 1
        skipped_players: set[Player] = set()
        all_players = set(gs.turn_order.players)

        while skipped_players != all_players:
            player = gs.turn_order.advance()
            activateable_units = [
                unit
                for unit in GS().map.units_controlled_by(player)
                if unit.can_be_activated()
            ]
            if not activateable_units:
                skipped_players.add(player)
                continue
            skipped_players.remove(player)

            ES.resolve(Turn(select_unit(activateable_units)))

        for unit in gs.map.unit_positions.keys():
            unit.exhausted = False


@dataclasses.dataclass
class Play(Event[None]):

    def resolve(self) -> None:
        gs = GS()
        while (
            not any(p.points >= gs.target_points for p in gs.turn_order.players)
            and gs.round_counter < 20
        ):
            ES.resolve(Round())
