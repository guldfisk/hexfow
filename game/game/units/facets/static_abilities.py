from __future__ import annotations

import dataclasses
from typing import ClassVar

from events.eventsystem import (
    TriggerEffect,
    ES,
    ReplacementEffect,
    StateModifierEffect,
    hook_on,
)
from game.game.core import (
    StaticAbilityFacet,
    Unit,
    Hex,
    GS,
    MeleeAttackFacet,
    ActiveUnitContext,
    SingleTargetAttackFacet,
    EffortOption,
    OneOfUnits,
    MoveOption,
    OneOfHexes,
    SkipOption,
    StatusSignature,
    DamageSignature,
    Source,
    Status,
    TerrainProtectionRequest,
)
from game.game.decisions import Option, NoTarget, SelectOptionDecisionPoint
from game.game.events import (
    SimpleAttack,
    Damage,
    MoveAction,
    MeleeAttackAction,
    MoveUnit,
    Kill,
    Heal,
    CheckAlive,
    MovePenalty,
    Turn,
    KillUpkeep,
    GainEnergy,
    ApplyStatus,
    TurnCleanup,
    SufferDamage,
)
from game.game.map.terrain import Water
from game.game.player import Player
from game.game.statuses import (
    Terrified,
    TheyVeGotASteelChair,
    MortallyWounded,
    Poison,
    Burn,
)
from game.game.values import DamageType, Resistance


@dataclasses.dataclass(eq=False)
class PricklyTrigger(TriggerEffect[SimpleAttack]):
    # TODO handle priority in shared enum or some shit
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source
    amount: int

    def should_trigger(self, event: SimpleAttack) -> bool:
        return event.defender == self.unit and isinstance(
            event.attack, MeleeAttackFacet
        )

    def resolve(self, event: SimpleAttack) -> None:
        ES.resolve(Damage(event.attacker, DamageSignature(self.amount, self.source)))


class Prickly(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.owner, self, 2))


# TODO just an example, should of course prevent the action being available in the first place
@dataclasses.dataclass(eq=False)
class NoMoveAction(ReplacementEffect[MoveAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def can_replace(self, event: MoveAction) -> bool:
        return event.unit == self.unit

    def resolve(self, event: MoveAction) -> None: ...


class Immobile(StaticAbilityFacet):
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
            and request.map.distance_between(self.unit, request.position) == 1
        )

    def modify(self, obj: Unit, request: Hex, value: bool) -> bool:
        return False


class Farsighted(StaticAbilityFacet):
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
            and GS().map.distance_between(self.unit, event.defender) <= 1
        )

    def resolve(self, event: MeleeAttackAction) -> None:
        ES.resolve(
            SimpleAttack(
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


class PackHunter(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PackHunterTrigger(self.owner))


@dataclasses.dataclass(eq=False)
class CrushableReplacement(ReplacementEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit

    def can_replace(self, event: MoveUnit) -> bool:
        return (
            self.unit.controller == event.unit.controller
            and event.to_ == GS().map.hex_off(self.unit)
        )

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Kill(self.unit))
        ES.resolve(Heal(event.unit, 1))
        ES.resolve(event)


@dataclasses.dataclass(eq=False)
class CrushableModifier(StateModifierEffect[Hex, Unit, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.is_occupied_for

    unit: Unit

    def should_modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return request.controller == self.unit.controller and obj == GS().map.hex_off(
            self.unit
        )

    def modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return True


class Nourishing(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            CrushableReplacement(self.owner), CrushableModifier(self.owner)
        )


@dataclasses.dataclass(eq=False)
class PusherModifier(StateModifierEffect[Hex, Unit, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.is_occupied_for

    unit: Unit

    def should_modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return request == self.unit

    def modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class PusherReplacement(ReplacementEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def can_replace(self, event: MoveUnit) -> bool:
        return event.unit == self.unit and GS().map.unit_on(event.to_)

    def resolve(self, event: MoveUnit) -> None:
        _map = GS().map
        direction = event.to_.position - _map.position_off(event.unit)

        unit_positions: list[tuple[Unit, Hex | None]] = []
        current_position = _map.position_off(event.unit)
        while True:
            current_position += direction
            current_unit = _map.unit_on(_map.hexes[current_position])
            if not current_unit:
                break
            next_position = current_position + direction
            if next_position not in _map.hexes:
                unit_positions.append((current_unit, None))
                break
            if _map.hexes[next_position].is_passable_to(current_unit):
                unit_positions.append((current_unit, _map.hexes[next_position]))
            else:
                unit_positions.append((current_unit, None))
                break

        for unit, target in reversed(unit_positions):
            moved = False
            if target:
                moved = any(
                    e.unit == unit
                    for e in ES.resolve(MoveUnit(unit, target)).iter_type(MoveUnit)
                )
            if not moved:
                # TODO should damage when move fails, even if the target wasn't non to begin with
                ES.resolve(Damage(unit, DamageSignature(1, self.source)))
                ES.resolve(CheckAlive(unit))

        if not _map.unit_on(event.to_):
            ES.resolve(event)


class Pusher(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.owner), PusherReplacement(self.owner, self)
        )


@dataclasses.dataclass(eq=False)
class PerTurnMovePenaltyIgnoreReplacement(ReplacementEffect[MovePenalty]):
    priority: ClassVar[int] = 0

    unit: Unit
    limit: int
    ignored_this_turn: int = dataclasses.field(init=False, default=0)

    @hook_on(Turn)
    def on_move_hook(self, event: Turn) -> None:
        self.ignored_this_turn = 0

    def can_replace(self, event: MovePenalty) -> bool:
        return event.unit == self.unit and self.ignored_this_turn < self.limit

    def resolve(self, event: MovePenalty) -> None:
        ignore_quantity = min(self.limit - self.ignored_this_turn, event.amount)
        self.ignored_this_turn += ignore_quantity
        event.branch(amount=event.amount - ignore_quantity)


class TerrainSavvy(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PerTurnMovePenaltyIgnoreReplacement(self.owner, 1))


@dataclasses.dataclass(eq=False)
class FuriousTrigger(TriggerEffect[SimpleAttack]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: SimpleAttack) -> bool:
        return event.defender == self.unit

    def resolve(self, event: SimpleAttack) -> None:
        self.unit.exhausted = False


class Furious(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(FuriousTrigger(self.owner))


@dataclasses.dataclass(eq=False)
class StealthModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = 1
    # TODO is_hidden_for should prob be is_hidden_for(unit) instead of for (player)
    target: ClassVar[object] = Unit.is_hidden_for

    unit: Unit

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return (
            obj == self.unit
            and request != self.unit.controller
            and not any(
                request in unit.provides_vision_for(None)
                and unit.can_see(GS().map.hex_off(self.unit))
                for unit in GS().map.get_neighboring_units_off(self.unit)
            )
        )

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return True


class Stealth(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(StealthModifier(self.owner))


@dataclasses.dataclass(eq=False)
class FightFlightFreezeModifier(
    StateModifierEffect[Unit, ActiveUnitContext, list[Option]]
):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_legal_options

    unit: Unit

    def should_modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> bool:
        return (
            obj.controller != self.unit.controller
            and GS().map.distance_between(self.unit, obj) <= 1
        )

    def modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> list[Option]:
        options = []
        for option in value:
            if (
                isinstance(option, EffortOption)
                and isinstance(option.facet, SingleTargetAttackFacet)
                and isinstance(option.target_profile, OneOfUnits)
                and self.unit in option.target_profile.units
            ):
                options.append(
                    EffortOption(option.facet, target_profile=OneOfUnits([self.unit]))
                )
            elif (
                isinstance(option, MoveOption)
                and isinstance(option.target_profile, OneOfHexes)
                and (
                    valid_hexes := [
                        _hex
                        for _hex in option.target_profile.hexes
                        if GS().map.distance_between(self.unit, _hex) > 1
                    ]
                )
            ):
                options.append(MoveOption(target_profile=OneOfHexes(valid_hexes)))
            elif isinstance(option, SkipOption):
                options.append(option)
        return options


class FightFlightFreeze(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(FightFlightFreezeModifier(self.owner))


@dataclasses.dataclass(eq=False)
class ExplosiveTrigger(TriggerEffect[KillUpkeep]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source
    damage: int

    def should_trigger(self, event: KillUpkeep) -> bool:
        return event.unit == self.unit

    def resolve(self, event: KillUpkeep) -> None:
        for unit in GS().map.get_units_within_range_off(self.unit, 1):
            ES.resolve(
                Damage(
                    unit, DamageSignature(self.damage, self.source, type=DamageType.AOE)
                )
            )


class Explosive(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(ExplosiveTrigger(self.owner, self, 5))


# TODO same trigger etc
@dataclasses.dataclass(eq=False)
class SchadenfreudeDamageTrigger(TriggerEffect[Damage]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: Damage) -> bool:
        return (
            event.unit != self.unit
            and GS().map.distance_between(self.unit, event.unit) <= 1
        )

    def resolve(self, event: Damage) -> None:
        ES.resolve(GainEnergy(self.unit, 1))


# TODO should only trigger on debuffs
@dataclasses.dataclass(eq=False)
class SchadenfreudeDebuffTrigger(TriggerEffect[ApplyStatus]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: ApplyStatus) -> bool:
        return (
            event.unit != self.unit
            and GS().map.distance_between(self.unit, event.unit) <= 1
        )

    def resolve(self, event: ApplyStatus) -> None:
        ES.resolve(GainEnergy(self.unit, 1))


class Schadenfreude(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(
            SchadenfreudeDamageTrigger(self.owner),
            SchadenfreudeDebuffTrigger(self.owner),
        )


# TODO originally this was for all simple attacks, but then the kill event isn't
#  a child. Cut of course hack it in some way, or just have multiple triggers,
#  but it only has a melee attack, and maybe it is more evocative anyways...
# TODO the vision based trigger is cool, but it has some pretty unintuitive interactions,
#  since the attacking unit with this ability will still block vision from where it
#  attacked, not the space it follows up into. This is kinda intentional, but weird,
#  so yeah.
@dataclasses.dataclass(eq=False)
class GrizzlyMurdererTrigger(TriggerEffect[MeleeAttackAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: MeleeAttackAction) -> bool:
        return event.attacker == self.unit and any(
            kill.unit == event.defender for kill in event.iter_type(Kill)
        )

    def resolve(self, event: MeleeAttackAction) -> None:
        # TODO formalize iterating copy
        for unit in GS().map.units:
            if unit.controller != self.unit.controller and unit.can_see(
                GS().map.hex_off(event.defender)
            ):
                ES.resolve(
                    ApplyStatus(
                        unit=unit,
                        by=self.unit.controller,
                        signature=StatusSignature(Terrified, duration=2),
                    )
                )


class GrizzlyMurderer(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(GrizzlyMurdererTrigger(self.owner))


# telepath {7pp} x1
# health 5, movement 3, sight 0, energy 5, M
# rouse
#     ability 3 energy
#     target other unit 3 range NLoS
#     -1 movement
#     activates target
# pacify
#     ability 3 energy
#     target other unit 3 range NLoS
#     -2 movement
#     applies pacified for 1 round
#         disarmed
#         +1 energy regen
# turn outwards
#     ability 3 energy
#     target other unit 2 range NLoS
#     -1 movement
#     applies far gazing for 2 rounds
#         +1 sight
#         cannot see adjacent hexes
# - adjacent enemy units also provide vision for this units controller


@dataclasses.dataclass(eq=False)
class TelepathicSpyModifier(StateModifierEffect[Unit, None, set[Player]]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.provides_vision_for

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: set[Player]) -> bool:
        return (
            obj.controller != self.unit.controller
            and GS().map.distance_between(self.unit, obj) <= 1
        )

    def modify(self, obj: Unit, request: None, value: set[Player]) -> set[Player]:
        return value | {self.unit.controller}


class TelepathicSpy(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(TelepathicSpyModifier(self.owner))


@dataclasses.dataclass(eq=False)
class CaughtInTheMatchTrigger(TriggerEffect[MoveAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: MoveAction) -> bool:
        return (
            event.unit.controller != self.unit.controller
            and GS().active_unit_context
            and GS().active_unit_context.unit == event.unit
            and any(
                move_event.unit == event.unit
                and move_event.result
                and GS().map.distance_between(self.unit, move_event.result) <= 1
                and GS().map.distance_between(self.unit, move_event.to_) > 1
                for move_event in event.iter_type(MoveUnit)
            )
        )

    def resolve(self, event: MoveAction) -> None:
        # TODO should be event. prob in reality this effect should be a replacement on
        #  movement penalties...
        GS().active_unit_context.movement_points -= 1


class CaughtInTheMatch(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(CaughtInTheMatchTrigger(self.owner))


@dataclasses.dataclass(eq=False)
class HeelTurnTrigger(TriggerEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: SufferDamage) -> bool:
        return event.unit == self.unit and event.result >= 4

    def resolve(self, event: SufferDamage) -> None:
        ES.resolve(
            ApplyStatus(
                unit=self.unit,
                by=self.unit.controller,
                signature=StatusSignature(TheyVeGotASteelChair),
            )
        )


class HeelTurn(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(HeelTurnTrigger(self.owner))


@dataclasses.dataclass(eq=False)
class QuickTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: TurnCleanup) -> bool:
        return event.unit == self.unit

    def resolve(self, event: TurnCleanup) -> None:
        options = [SkipOption(target_profile=NoTarget())]
        if moveable_hexes := self.unit.get_potential_move_destinations(None):
            options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))

        decision = GS().make_decision(
            self.unit.controller,
            SelectOptionDecisionPoint(options, explanation="quick"),
        )
        if isinstance(decision.option, MoveOption):
            ES.resolve(MoveAction(self.unit, to_=decision.target))


class Quick(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(QuickTrigger(self.owner))


@dataclasses.dataclass(eq=False)
class SourceTypeResistance(StateModifierEffect[Unit, DamageSignature, Resistance]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_resistance_against

    unit: Unit
    source_type: type[Source]
    resistance: Resistance

    def should_modify(
        self, obj: Unit, request: DamageSignature, value: Resistance
    ) -> bool:
        return (
            obj == self.unit
            and request.source
            and isinstance(request.source, self.source_type)
        )

    def modify(
        self, obj: Unit, request: DamageSignature, value: Resistance
    ) -> Resistance:
        return max(value, self.resistance)


class GlassSkin(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.owner, Status, Resistance.MAJOR)
        )


class DiamondSkin(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.owner, Status, Resistance.IMMUNE)
        )


class FlameResistant(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(SourceTypeResistance(self.owner, Burn, Resistance.MAJOR))


@dataclasses.dataclass(eq=False)
class LastStandReplacement(ReplacementEffect[Kill]):
    priority: ClassVar[int] = 0

    unit: Unit

    def can_replace(self, event: Kill) -> bool:
        return event.unit == self.unit and not any(
            isinstance(status, MortallyWounded) for status in event.unit.statuses
        )

    def resolve(self, event: Kill) -> None:
        event.unit.damage = event.unit.max_health.g() - 1
        # TODO dispell debuffs
        ES.resolve(
            ApplyStatus(
                event.unit,
                event.unit.controller,
                StatusSignature(MortallyWounded, duration=1),
            )
        )


class LastStand(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(LastStandReplacement(self.owner))


@dataclasses.dataclass(eq=False)
class ToxicPresenceTrigger(TriggerEffect[TurnCleanup]):
    # TODO handle priority in shared enum or some shit
    priority: ClassVar[int] = 0

    unit: Unit
    amount: int

    def should_trigger(self, event: TurnCleanup) -> bool:
        return event.unit == self.unit

    def resolve(self, event: TurnCleanup) -> None:
        for unit in GS().map.get_neighboring_units_off(self.unit):
            ES.resolve(
                ApplyStatus(
                    unit,
                    self.unit.controller,
                    StatusSignature(Poison, stacks=self.amount),
                )
            )


class ToxicPresence(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(ToxicPresenceTrigger(self.owner, 1))


# otter scout {4w} x2
# health 5, movement 3, sight 2, S
# bite
#     melee attack
#     2 damage
# - aquatic
# - ignores move penalties on wet terrain
# - +1 terrain protection on wet terrain


@dataclasses.dataclass(eq=False)
class WaterTerrainProtectionModifier(
    StateModifierEffect[Unit, TerrainProtectionRequest, int]
):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_terrain_protection_for

    unit: Unit
    amount: int

    def should_modify(
        self, obj: Unit, request: TerrainProtectionRequest, value: int
    ) -> bool:
        return obj == self.unit and isinstance(
            GS().map.hex_off(self.unit).terrain, Water
        )

    def modify(self, obj: Unit, request: TerrainProtectionRequest, value: int) -> int:
        return value + self.amount


class Diver(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(WaterTerrainProtectionModifier(self.owner, 1))
