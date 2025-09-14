from events.eventsystem import ES
from events.tests.game_objects.advanced_units import Player
from game.core import (
    HexStatus,
    HighestStackableRefreshableMixin,
    LowestRefreshableMixin,
    PerPlayerRefreshable,
    PerPlayerUnstackable,
    RefreshableMixin,
    Terrain,
)
from game.effects.modifiers import (
    HexAttackPowerFlatModifier,
    HexBlocksVisionModifier,
    HexCappedFlatSightModifier,
    HexFlatEnergyRegenModifier,
    HexFlatSightModifier,
    HexMoveOutPenaltyModifier,
    HexRevealedModifier,
    MappedOutModifier,
)
from game.effects.triggers import (
    BurnOnCleanup,
    BurnOnWalkIn,
    HexRoundDamageTrigger,
    HexRoundHealTrigger,
    HexWalkInDamageTrigger,
    MineTrigger,
    ShrineSkipTrigger,
    ShrineWalkInTrigger,
    SludgeTrigger,
    TurnExpiringStatusTrigger,
    WalkInDestroyStatusTrigger,
)
from game.events import ChangeHexTerrain


class Shrine(HexStatus):
    """
    Units on this hex has +1 energy regeneration.
    When a unit moves into this space, it gains 1 stack of <fortified> for 4 rounds.
    When a unit skips it's within 1 range of this hex, it is healed 1.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexFlatEnergyRegenModifier(self.parent, 1),
            ShrineWalkInTrigger(self.parent, self),
            ShrineSkipTrigger(self.parent, self),
        )


class Soot(RefreshableMixin, HexStatus):
    """
    This hex blocks vision, and units on it has -1 sight, to a minimum of 1.
    When a unit moves into this hex, and at the end of the round, units on this hex are dealt 1 pure damage.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexWalkInDamageTrigger(self.parent, self, 1),
            HexRoundDamageTrigger(self.parent, self, 1),
            HexCappedFlatSightModifier(self.parent),
            HexBlocksVisionModifier(self.parent),
        )


class Smoke(RefreshableMixin, HexStatus):
    """
    This hex blocks vision, and units on it has -1 sight, to a minimum of 1.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexCappedFlatSightModifier(self.parent),
            HexBlocksVisionModifier(self.parent),
        )


class InkCloud(RefreshableMixin, HexStatus):
    """
    This hex blocks vision, and units on it has -1 sight.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexFlatSightModifier(self.parent, -1),
            HexBlocksVisionModifier(self.parent),
        )


class BurningTerrain(HighestStackableRefreshableMixin, HexStatus):
    """
    When a unit moves into this hex, and at the end of the round, apply stacks of <burn> equals to the stacks of this status to unit on this hex.
    """

    def create_effects(self) -> None:
        self.register_effects(
            BurnOnWalkIn(self.parent, lambda: self.stacks),
            BurnOnCleanup(self.parent, lambda: self.stacks),
        )


class Revealed(PerPlayerRefreshable, HexStatus):
    """
    You have vision of this hex. This status is hidden for opponents.
    """

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(HexRevealedModifier(self.parent, self.controller))


class Flare(PerPlayerRefreshable, HexStatus):
    """
    All players have vision of this hex
    """

    def create_effects(self) -> None:
        self.register_effects(HexRevealedModifier(self.parent, None))


class Glimpse(PerPlayerUnstackable, HexStatus):
    """
    This hex is visible to the controller of this status. Expires at the end of the turn.
    This status is hidden for opponents.
    """

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(
            HexRevealedModifier(self.parent, self.controller),
            TurnExpiringStatusTrigger(self),
        )


class MappedOut(PerPlayerUnstackable, HexStatus):
    """
    Units with the same controller as this status ignore move in penalties on this hex.
    This status is hidden for opponents.
    """

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(MappedOutModifier(self.parent, self.controller))


class DoombotScaffold(HexStatus):
    """
    Removed when a unit moves into this hex.
    """

    def create_effects(self) -> None:
        self.register_effects(WalkInDestroyStatusTrigger(self))


class RuneOfHealing(HexStatus):
    """
    At the end of each round, units on this hex are healed 1.
    """

    dispellable = False

    def create_effects(self) -> None:
        self.register_effects(HexRoundHealTrigger(self.parent, 1, self))


class UndergroundSpring(LowestRefreshableMixin, HexStatus):
    """
    When this status expires, change the terrain of this hex to Water.
    """

    def on_expires(self) -> None:
        ES.resolve(ChangeHexTerrain(self.parent, Terrain.get_class("water")))


class SappingField(RefreshableMixin, HexStatus):
    """
    Units on this hex has -1 attack power and energy regeneration.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexFlatEnergyRegenModifier(self.parent, -1),
            HexAttackPowerFlatModifier(self.parent, -1),
        )


class RuneOfClarity(HexStatus):
    """
    Units on this hex has +1 energy regeneration.
    """

    dispellable = False

    def create_effects(self) -> None:
        self.register_effects(HexFlatEnergyRegenModifier(self.parent, 1))


class Mine(HexStatus):
    """
    When a unit moves into this hex, it's dealt 2 damage and this status is removed.
    This status is hidden for opponents.
    """

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(MineTrigger(self))


class Sludge(RefreshableMixin, HexStatus):
    """
    +1 move out penalty. At the end of each round, applies <slimed> to unit on this hex for 2 rounds.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HexMoveOutPenaltyModifier(self.parent, 1), SludgeTrigger(self)
        )


class Gate(HexStatus):
    """
    If a unit would move into this hex, it instead moves into the hex with the linked gate, if able.
    """
