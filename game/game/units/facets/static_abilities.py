from __future__ import annotations

import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES, ReplacementEffect
from game.game.core import StatickAbilityFacet, Unit
from game.game.events import MeleeAttack, Damage, MoveAction


@dataclasses.dataclass(eq=False)
class PricklyTrigger(TriggerEffect[MeleeAttack]):
    # TODO handle priority in shared enum or some shit
    priority: ClassVar[int] = 0

    unit: Unit
    amount: int

    def should_trigger(self, event: MeleeAttack) -> bool:
        return event.defender == self.unit and not self.unit.is_broken.g()

    def resolve(self, event: MeleeAttack) -> None:
        ES.resolve(Damage(event.attacker, self.amount))


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
