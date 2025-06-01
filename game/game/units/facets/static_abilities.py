from __future__ import annotations

import dataclasses
from typing import ClassVar

from events.eventsystem import (
    TriggerEffect,
    ES,
    ReplacementEffect,
    StateModifierEffect,
    E,
)
from game.game.core import StatickAbilityFacet, Unit, Hex, GS, MeleeAttackFacet
from game.game.damage import DamageSignature
from game.game.events import MeleeAttack, Damage, MoveAction, MeleeAttackAction
from game.game.values import DamageType


@dataclasses.dataclass(eq=False)
class PricklyTrigger(TriggerEffect[MeleeAttack]):
    # TODO handle priority in shared enum or some shit
    priority: ClassVar[int] = 0

    unit: Unit
    amount: int

    def should_trigger(self, event: MeleeAttack) -> bool:
        return event.defender == self.unit and not self.unit.is_broken.g()

    def resolve(self, event: MeleeAttack) -> None:
        ES.resolve(Damage(event.attacker, DamageSignature(self.amount)))


class Prickly(StatickAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.owner, 2))


# TODO just an example, should of course prevent the action being available in the first place
@dataclasses.dataclass(eq=False)
class NoMoveAction(ReplacementEffect[MoveAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def can_replace(self, event: MoveAction) -> bool:
        return event.unit == self.unit

    def resolve(self, event: MoveAction) -> None:
        ...


class Immobile(StatickAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(NoMoveAction(self.owner))


@dataclasses.dataclass(eq=False)
class FarsightedModifier(StateModifierEffect[Unit, Hex, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.can_see

    unit: Unit

    def should_modify(self, obj: Unit, request: Hex, value: int) -> bool:
        return (
            obj == self.unit
            and request.map.position_of(self.unit).position.distance_to(
                request.position
            )
            == 1
        )

    def modify(self, obj: Unit, request: Hex, value: bool) -> bool:
        return False


class Farsighted(StatickAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(FarsightedModifier(self.owner))


@dataclasses.dataclass(eq=False)
class PackHunterTrigger(TriggerEffect[MeleeAttackAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: MeleeAttackAction) -> bool:
        return (
            event.defender.controller != self.unit.controller
            and event.attacker != self.unit
            # TODO really awkward having to be defencive about this here, maybe
            #  good argument for triggers being queued before event execution?
            and event.defender.on_map()
            and GS()
            .map.position_of(self.unit)
            .position.distance_to(GS().map.position_of(event.defender).position)
            <= 1
        )

    def resolve(self, event: MeleeAttackAction) -> None:
        ES.resolve(
            MeleeAttack(
                attacker=self.unit,
                defender=event.defender,
                # TODO yikes
                attack=next(
                    iter(
                        facet
                        for facet in self.unit.attacks
                        if isinstance(facet, MeleeAttackFacet)
                    )
                ),
            )
        )


class PackHunter(StatickAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PackHunterTrigger(self.owner))
