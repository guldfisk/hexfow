import dataclasses
from typing import Self, ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import UnitStatus, GS
from game.game.damage import DamageSignature
from game.game.events import Damage, Upkeep
from game.game.values import DamageType


@dataclasses.dataclass(eq=False)
class BurnTrigger(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: Upkeep) -> None:
        ES.resolve(Damage(self.status.parent, DamageSignature(self.status.stacks)))
        self.status.decrement_stacks()


# TODO what should the order off trigger be for burn vs decrement and such?
class Burn(UnitStatus):
    identifier = "burn"

    def merge(self, incoming: Self) -> bool:
        self.stacks += incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(BurnTrigger(self))


# TODO timings (right now only get to trigger duration -1 times)
@dataclasses.dataclass(eq=False)
class PanickedTrigger(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: Upkeep) -> None:
        ES.resolve(
            Damage(
                self.status.parent,
                DamageSignature(
                    len(list(GS().map.get_neighboring_units_off(self.status.parent))),
                    type=DamageType.TRUE,
                ),
            )
        )


class Panicked(UnitStatus):
    identifier = "panicked"

    def merge(self, incoming: Self) -> bool:
        if incoming.duration > self.duration:
            self.duration = incoming.duration
            self.original_duration = incoming.original_duration
            return True
        return False

    def create_effects(self) -> None:
        self.register_effects(PanickedTrigger(self))
