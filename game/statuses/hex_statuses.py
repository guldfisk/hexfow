from typing import Self

from events.tests.game_objects.advanced_units import Player
from game.core import HexStatus, DurationStatusMixin
from game.effects.modifiers import (
    HexIncreasesEnergyRegenModifier,
    HexDecreaseSightCappedModifier,
    HexBlocksVisionModifier,
    HexRevealedModifier,
)
from game.effects.triggers import (
    ShrineWalkInTrigger,
    ShrineSkipTrigger,
    HexWalkInDamageTrigger,
    HexRoundDamageTrigger,
    BurnOnWalkIn,
    BurnOnCleanup,
    TurnExpiringStatusTrigger,
    WalkInDestroyStatusTrigger,
)


class Shrine(HexStatus):

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(
            HexIncreasesEnergyRegenModifier(self.parent, 1),
            ShrineWalkInTrigger(self.parent, self),
            ShrineSkipTrigger(self.parent),
        )


class Soot(DurationStatusMixin, HexStatus):

    def create_effects(self) -> None:
        self.register_effects(
            HexWalkInDamageTrigger(self.parent, self, 1),
            HexRoundDamageTrigger(self.parent, self, 1),
            HexDecreaseSightCappedModifier(self.parent),
            HexBlocksVisionModifier(self.parent),
        )


class Smoke(DurationStatusMixin, HexStatus):
    """
    This hex blocks vision, and units on it has -1 sight, to a minimum of 1.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexDecreaseSightCappedModifier(self.parent),
            HexBlocksVisionModifier(self.parent),
        )


class BurningTerrain(HexStatus):
    """
    When a unit moves into this hex, and at the end of the round, units on this hex suffers 1 burn.
    """

    related_statuses = ["burn"]

    def merge(self, incoming: Self) -> bool:
        # TODO common logic?
        if not self.duration is None and (
            incoming.duration is None or (incoming.duration > self.duration)
        ):
            self.duration = incoming.duration
        if incoming.stacks > self.stacks:
            self.stacks = incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(
            BurnOnWalkIn(self.parent, lambda: self.stacks),
            BurnOnCleanup(self.parent, lambda: self.stacks),
        )


class Revealed(HexStatus):
    def merge(self, incoming: Self) -> bool:
        # TODO common logic?
        if incoming.controller == self.controller:
            if not self.duration is None and (
                incoming.duration is None or (incoming.duration > self.duration)
            ):
                self.duration = incoming.duration
            return True
        return False

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(HexRevealedModifier(self.parent, self.controller))


# TODO how should this work with the turn immediately ending?
class Glimpse(HexStatus):
    def merge(self, incoming: Self) -> bool:
        return incoming.controller == self.controller

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(
            HexRevealedModifier(self.parent, self.controller),
            TurnExpiringStatusTrigger(self),
        )


class DoombotScaffold(HexStatus):
    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(WalkInDestroyStatusTrigger(self))
