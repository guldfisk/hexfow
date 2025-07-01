from typing import Self

from events.eventsystem import ES
from game.core import UnitStatus, RefreshableDurationUnitStatus
from game.effects.modifiers import (
    RootedModifier,
    UnitAttackPowerFlatModifier,
    UnitMaxHealthFlatModifier,
    TerrorModifier,
    UnitProportionalSpeedModifier,
    UnitSizeFlatModifier,
)
from game.effects.replacements import LuckyCharmReplacement
from game.effects.triggers import (
    BurnTrigger,
    TurnExpiringStatusTrigger,
    RoundDamageTrigger,
    PanickedTrigger,
    ParasiteTrigger,
    OneTimeModifyMovementPointsStatusTrigger,
    BellStruckTrigger,
)
from game.events import Kill
from game.values import StatusIntention


class Burn(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        self.stacks += incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(BurnTrigger(self))


class Poison(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        self.stacks += incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(
            RoundDamageTrigger(self.parent, self, lambda: self.stacks)
        )


class Panicked(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(PanickedTrigger(self))


class Ephemeral(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        if incoming.duration < self.duration:
            self.duration = incoming.duration
            return True
        return False

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent))


class Terrified(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, -1))


class Parasite(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    # TODO ABC for this
    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(ParasiteTrigger(self))


class BurstOfSpeed(UnitStatus):
    default_intention = StatusIntention.BUFF

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(OneTimeModifyMovementPointsStatusTrigger(self, 1))


class Stumbling(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(OneTimeModifyMovementPointsStatusTrigger(self, -1))


class TheyVeGotASteelChair(UnitStatus):
    default_intention = StatusIntention.BUFF

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, 2))


class Staggered(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(TurnExpiringStatusTrigger(self))


class AllInJest(UnitStatus):
    default_intention = StatusIntention.BUFF

    def merge(self, incoming: Self) -> bool:
        if incoming.stacks:
            self.stacks += incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(
            TurnExpiringStatusTrigger(self),
            UnitAttackPowerFlatModifier(self.parent, lambda: self.stacks),
        )


class Rooted(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(RootedModifier(self.parent))


class Fortified(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(UnitMaxHealthFlatModifier(self.parent, 1))


class LuckyCharm(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(LuckyCharmReplacement(self))


class BellStruck(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(BellStruckTrigger(self.parent))


class MortallyWounded(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        return True

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent))


class Terror(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(TerrorModifier(self.parent))


class DebilitatingVenom(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitAttackPowerFlatModifier(self.parent, -1),
            UnitProportionalSpeedModifier(self.parent, 0.5),
        )


class Shrunk(UnitStatus):

    def merge(self, incoming: Self) -> bool:
        if not self.duration is None and (
            incoming.duration is None or (incoming.duration > self.duration)
        ):
            self.duration = incoming.duration
        self.stacks += incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(
            UnitAttackPowerFlatModifier(self.parent, lambda: -self.stacks),
            UnitSizeFlatModifier(self.parent, lambda: -self.stacks),
            UnitMaxHealthFlatModifier(self.parent, lambda: -self.stacks * 2),
        )
