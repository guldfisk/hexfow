from __future__ import annotations

import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.events import MeleeAttack, Damage
from game.game.units.unit import Unit, StatickAbilityFacet


@dataclasses.dataclass(eq=False)
class PricklyTrigger(TriggerEffect[MeleeAttack]):
    priority: ClassVar[int] = 0

    unit: Unit
    amount: int

    def should_trigger(self, event: MeleeAttack) -> bool:
        return event.defender == self.unit

    def resolve(self, event: MeleeAttack) -> None:
        ES.resolve(Damage(event.attacker, self.amount))


class Prickly(StatickAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.owner, 2))
