from __future__ import annotations

import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES, ReplacementEffect, StateModifierEffect
from game.game.core import StatickAbilityFacet, Unit, Hex, GS
from game.game.damage import DamageSignature
from game.game.events import MeleeAttack, Damage, MoveAction
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

    def resolve(self, event: MoveAction) -> None: ...


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
