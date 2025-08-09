from __future__ import annotations

import contextlib
import dataclasses
import itertools
import re
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import (
    ClassVar,
    Literal,
    Any,
    TypeVar,
    Iterator,
    Generic,
    Self,
    Iterable,
    TypeAlias,
    Callable,
)
from typing import Mapping

from bidict import bidict

from events.eventsystem import (
    Modifiable,
    ModifiableAttribute,
    modifiable,
)
from game.decisions import (
    DecisionPoint,
    Option,
    TargetProfile,
    O,
    JSON,
    NoTarget,
    Serializable,
    SerializationContext,
    IDMap,
)
from game.has_effects import HasEffects
from game.info.registered import Registered, get_registered_meta, UnknownIdentifierError
from game.interface import Connection
from game.map.coordinates import CC, line_of_sight_obstructed, Corner, CornerPosition
from game.map.geometry import hex_circle, hex_ring, hex_arc
from game.player import Player
from game.turn_order import TurnOrder
from game.values import (
    Size,
    DamageType,
    VisionObstruction,
    StatusIntention,
    Resistance,
)


A = TypeVar("A", bound=DecisionPoint)
T = TypeVar("T")
S = TypeVar("S")


# TODO wtf if this
class VisionBound(Serializable):
    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"id": context.id_map.get_id_for(self), **self.serialize_values(context)}


class MoveOption(Option[O]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


@dataclasses.dataclass
class EffortOption(Option[O]):
    facet: EffortFacet

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"facet": self.facet.serialize_type()}


@dataclasses.dataclass
class ActivateUnitOption(Option[O]):
    actions_previews: dict[Unit, list[Option]]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "actions_preview": {
                context.id_map.get_id_for(unit): [
                    option.serialize(context) for option in options
                ]
                for unit, options in self.actions_previews.items()
            }
        }


class SkipOption(Option[None]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


@dataclasses.dataclass
class HasStatuses(HasEffects, Generic[S]):
    statuses: list[Status] = dataclasses.field(default_factory=list, init=False)

    def add_status(self, status: S) -> S:
        if not status.on_apply(self):
            # TODO should return None instead?
            return status
        # TODO should prob set parent
        for existing_status in self.statuses:
            if type(existing_status) == type(status) and existing_status.merge(status):
                return existing_status
        self.statuses.append(status)
        status.create_effects()
        return status

    def get_statuses(self, status_type: type[S]) -> list[S]:
        return [status for status in self.statuses if isinstance(status, status_type)]

    def has_status(self, status_type: type[Status] | str) -> bool:
        status_type = (
            Status.registry[status_type]
            if isinstance(status_type, str)
            else status_type
        )
        return any(isinstance(status, status_type) for status in self.statuses)

    def remove_status(self, status: Status) -> None:
        try:
            self.statuses.remove(status)
        except ValueError:
            pass
        status.deregister()


H = TypeVar("H", bound=HasStatuses)


# TODO a facet should not have statuses
class Facet(HasStatuses, Modifiable, Registered, ABC, metaclass=get_registered_meta()):
    registry: ClassVar[dict[str, Facet]]

    def __init__(self, owner: Unit):
        super().__init__(parent=owner)

        # TODO should be able to unify this with parent from has_statuses or whatever
        self.owner = owner

    # TODO common interface?
    def create_effects(self) -> None: ...

    # TODO lmao
    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
            "related_statuses": cls.related_statuses,
        }


class EffortCost(ABC):

    @abstractmethod
    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        pass

    @abstractmethod
    def pay(self, context: ActiveUnitContext) -> None:
        pass

    @classmethod
    @abstractmethod
    def merge(cls, instances: list[Self]) -> Self: ...

    def __or__(self, other: EffortCost | EffortCostSet) -> EffortCostSet:
        return EffortCostSet(
            [self, other]
            if isinstance(other, EffortCost)
            else [self, *other.costs.values()]
        )

    @abstractmethod
    def serialize_values(self) -> dict[str, Any]: ...

    def serialize(self) -> dict[str, Any]:
        return {"type": self.__class__.__name__, **self.serialize_values()}


Co = TypeVar("Co", bound=EffortCost)


class EffortCostSet:

    def __init__(self, costs: Iterable[EffortCost] = ()):
        grouped: dict[type[EffortCost], list[EffortCost]] = defaultdict(list)
        for cost in costs:
            grouped[type(cost)].append(cost)
        self.costs = {
            cost_type: cost_type.merge(_costs) for cost_type, _costs in grouped.items()
        }

    def get(self, cost_type: type[Co]) -> Co | None:
        return self.costs.get(cost_type)

    @abstractmethod
    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return all(cost.can_be_paid(context) for cost in self.costs.values())

    @abstractmethod
    def pay(self, context: ActiveUnitContext) -> None:
        for cost in self.costs.values():
            cost.pay(context)

    def __or__(self, other: EffortCost | EffortCostSet) -> EffortCostSet:
        return EffortCostSet(
            [*self.costs.values(), other]
            if isinstance(other, EffortCost)
            else [self.costs.values(), *other.costs.values()]
        )

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__, ", ".join(str(c) for c in self.costs.values())
        )

    def __bool__(self) -> bool:
        return bool(self.costs)

    def serialize(self) -> dict[str, Any]:
        return {"atoms": [cost.serialize() for cost in self.costs.values()]}


@dataclasses.dataclass
class MovementCost(EffortCost):
    amount: int

    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return not context.has_acted or self.amount <= context.movement_points

    def pay(self, context: ActiveUnitContext) -> None:
        context.movement_points -= self.amount

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls(amount=sum(cost.amount for cost in instances))

    def serialize_values(self) -> dict[str, Any]:
        return {"amount": self.amount}


class ExclusiveCost(EffortCost):

    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return not context.has_acted

    def pay(self, context: ActiveUnitContext) -> None:
        context.movement_points = min(context.movement_points, 0)
        context.should_stop = True

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls()

    def serialize_values(self) -> dict[str, Any]:
        return {}


@dataclasses.dataclass
class EnergyCost(EffortCost):
    amount: int

    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return self.amount <= context.unit.energy

    def pay(self, context: ActiveUnitContext) -> None:
        context.unit.energy -= self.amount

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls(amount=sum(cost.amount for cost in instances))

    def serialize_values(self) -> dict[str, Any]:
        return {"amount": self.amount}


class EffortFacet(Facet, Modifiable, ABC):
    cost: ClassVar[EffortCostSet | EffortCost | None] = None
    # TODO these should be some signature together
    combinable: ClassVar[bool] = False
    max_activations: int | None = 1

    # TODO how does overriding work with modifiable? also, can it be abstract?
    @modifiable
    def get_legal_targets(self, context: ActiveUnitContext) -> list[Unit]: ...

    @classmethod
    def get_cost_set(cls) -> EffortCostSet:
        if isinstance(cls.cost, EffortCost):
            return EffortCostSet([cls.cost])
        return cls.cost or EffortCostSet()

    # TODO should prob be modifyable. prob need some way to lock in costs for effort
    #  options then.
    def get_cost(self) -> EffortCostSet:
        return self.get_cost_set()

    # TODO how does overriding work with modifiable?
    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            (
                self.max_activations is None
                or context.activated_facets[self.__class__.__name__]
                < self.max_activations
            )
            and self.get_cost().can_be_paid(context)
            and self.get_legal_targets(context)
        )

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            **super().serialize_type(),
            "cost": cls.get_cost_set().serialize(),
            "combineable": cls.combinable,
            "max_activations": cls.max_activations,
        }


class AttackFacet(EffortFacet, ABC): ...


# TODO cleanup typevar definitions and names
C = TypeVar("C", bound=AttackFacet)


# TODO maybe this is all attacks, and "aoe attacks" are all abilities?
#  Don't think so, but it should prob be called something different.
class SingleTargetAttackFacet(AttackFacet, ABC):
    damage_type: ClassVar[DamageType]
    damage: ClassVar[int]
    ap: ClassVar[int] = 0

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        # TODO blah internal hook
        ...

    @modifiable
    def get_damage_signature_against(self, unit: Unit) -> DamageSignature:
        return DamageSignature(
            max(
                self.damage
                + (self.get_damage_modifier_against(unit) or 0)
                + self.owner.attack_power.g(),
                0,
            ),
            self,
            type=self.damage_type,
            ap=self.ap,
        )

    def resolve_pre_damage_effects(self, defender: Unit) -> None: ...
    def resolve_post_damage_effects(self, defender: Unit) -> None: ...

    @classmethod
    def serialize_type(cls) -> JSON:
        return {**super().serialize_type(), "damage": cls.damage, "ap": cls.ap}


class MeleeAttackFacet(SingleTargetAttackFacet, ABC):
    category = "melee_attack"
    damage_type = DamageType.MELEE

    @modifiable
    def get_legal_targets(self, context: ActiveUnitContext) -> list[Unit]:
        return [
            unit
            for unit in GS.map.get_neighboring_units_off(self.owner)
            if unit.controller != self.owner.controller
            and unit.is_visible_to(self.owner.controller)
            and unit.can_be_attacked_by(self)
            and GS.map.hex_off(unit).is_passable_to(self.owner)
            and (
                not context.has_acted
                or GS.map.hex_off(unit).get_move_in_cost_for(self.owner)
                + (self.get_cost().get(MovementCost) or MovementCost(0)).amount
                <= context.movement_points
            )
        ]

    # TODO should prob be modifiable.
    def should_follow_up(self) -> bool:
        return True


# TODO where should logic for these be?
def is_vision_obstructed_for_unit_at(unit: Unit, cc: CC) -> bool:
    match GS.vision_obstruction_map[unit.controller].get(cc):
        case VisionObstruction.FULL:
            return True
        case VisionObstruction.FOR_LOW_GROUND:
            return not GS.map.hex_off(unit).terrain.is_high_ground
        case _:
            return False


def line_of_sight_obstructed_for_unit(unit: Unit, line_from: CC, line_to: CC) -> bool:
    return line_of_sight_obstructed(
        line_from, line_to, lambda cc: is_vision_obstructed_for_unit_at(unit, cc)
    )


class RangedAttackFacet(SingleTargetAttackFacet, ABC):
    category = "ranged_attack"
    damage_type = DamageType.RANGED
    range: ClassVar[int]

    @modifiable
    def get_legal_targets(self, context: ActiveUnitContext) -> list[Unit]:
        return [
            unit
            for unit in GS.map.get_units_within_range_off(self.owner, self.range)
            if unit.controller != self.owner.controller
            # TODO test on this
            and unit.is_visible_to(self.owner.controller)
            and not line_of_sight_obstructed_for_unit(
                self.owner,
                GS.map.position_off(self.owner),
                GS.map.position_off(unit),
            )
            and unit.can_be_attacked_by(self)
        ]

    @classmethod
    def serialize_type(cls) -> JSON:
        return {**super().serialize_type(), "range": cls.range}


class ActivatedAbilityFacet(EffortFacet, Generic[O], ABC):
    category = "activated_ability"

    @abstractmethod
    def get_target_profile(self) -> TargetProfile[O] | None: ...

    @abstractmethod
    def perform(self, target: O) -> None: ...

    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            (
                self.max_activations is None
                or context.activated_facets[self.__class__.__name__]
                < self.max_activations
            )
            and self.get_cost().can_be_paid(context)
            and self.get_target_profile() is not None
        )


class StaticAbilityFacet(Facet, ABC):
    category = "static_ability"


class Status(
    Registered, HasEffects[H], Serializable, ABC, metaclass=get_registered_meta()
):
    registry: ClassVar[dict[str, Status]]

    def __init__(
        self,
        *,
        # TODO this is redundante with the source
        controller: Player | None = None,
        source: Source = None,
        duration: int | None = None,
        stacks: int | None = None,
        parent: H | None,
    ):
        super().__init__(parent=parent)
        self.controller = controller
        self.source = source
        self.duration = duration
        self.stacks = stacks

    def on_apply(self, to: H) -> bool:
        return True

    def merge(self, incoming: Self) -> bool:
        return False

    def is_hidden_for(self, player: Player) -> bool:
        return False

    def create_effects(self) -> None: ...

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
            "related_statuses": cls.related_statuses,
        }

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "type": self.identifier,
            "duration": self.duration,
            "stacks": self.stacks,
        }

    def on_expires(self) -> None:
        # TODO blah
        pass

    def remove(self) -> None:
        # TODO is this all?
        self.parent.remove_status(self)

    def decrement_duration(self) -> None:
        if self.duration is None:
            return
        self.duration -= 1
        if self.duration <= 0:
            self.on_expires()
            self.remove()

    def decrement_stacks(self) -> None:
        self.stacks -= 1
        if self.stacks <= 0:
            self.remove()


FULL_ENERGY: Literal["FULL_ENERGY"] = "FULL_ENERGY"


class UnitBlueprint:
    registry: ClassVar[dict[str, UnitBlueprint]] = {}

    def __init__(
        self,
        name: str,
        *,
        health: int,
        speed: int,
        sight: int,
        armor: int = 0,
        energy: int = 0,
        starting_energy: int | FULL_ENERGY = FULL_ENERGY,
        size: Size = Size.MEDIUM,
        # TODO should this be a stat?
        aquatic: bool = False,
        facets: list[type[Facet]] | None = None,
        price: int | None,
        max_count: int = 1,
        identifier: str | None = None,
    ):
        self.name = name
        self.health = health
        self.speed = speed
        self.sight = sight
        self.armor = armor
        self.energy = energy
        self.starting_energy = starting_energy
        self.size = size
        self.aquatic = aquatic
        self.facets = facets or []
        self.identifier = identifier or re.sub(
            "_+", "_", re.sub("[^a-z]", "_", self.name.lower())
        )
        self.registry[self.identifier] = self

        self.price = price
        self.max_count = max_count

    @classmethod
    def get_class(cls, identifier: str) -> Self:
        try:
            return cls.registry[identifier]
        except KeyError:
            raise UnknownIdentifierError(cls, identifier)

    def __repr__(self):
        return f"{type(self).__name__}({self.name})"

    def serialize(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            # TODO how should this work?
            "small_image": f"/src/images/units/{self.identifier}_small.png",
            "health": self.health,
            "speed": self.speed,
            "sight": self.sight,
            "armor": self.armor,
            "energy": self.energy,
            # TODO
            "size": self.size.name[0],
            "aquatic": self.aquatic,
            "facets": [facet.identifier for facet in self.facets],
            "price": self.price,
        }


class Unit(HasStatuses, Modifiable, VisionBound):
    speed: ModifiableAttribute[None, int]
    sight: ModifiableAttribute[None, int]
    max_health: ModifiableAttribute[None, int]
    armor: ModifiableAttribute[None, int]
    max_energy: ModifiableAttribute[None, int]
    energy_regen: ModifiableAttribute[None, int]
    size: ModifiableAttribute[None, Size]
    attack_power: ModifiableAttribute[None, int]
    aquatic: ModifiableAttribute[None, bool]
    is_broken: ModifiableAttribute[None, bool]

    statuses: list[UnitStatus]

    def __init__(
        self, controller: Player, blueprint: UnitBlueprint, exhausted: bool = False
    ):
        super().__init__()

        self.controller = controller
        self.blueprint = blueprint

        self.damage: int = 0
        self.max_health.set(blueprint.health)
        self.speed.set(blueprint.speed)
        self.sight.set(blueprint.sight)
        self.armor.set(blueprint.armor)
        self.max_energy.set(blueprint.energy)
        self.energy_regen.set(1)
        self.energy: int = (
            blueprint.starting_energy
            if isinstance(blueprint.starting_energy, int)
            else blueprint.energy
        )
        self.size.set(blueprint.size)
        self.attack_power.set(0)
        self.aquatic.set(blueprint.aquatic)
        self.is_broken.set(False)
        self.exhausted = exhausted

        self.attacks: list[AttackFacet] = []
        self.activated_abilities: list[ActivatedAbilityFacet] = []
        self.static_abilities: list[StaticAbilityFacet] = []

        for facet in blueprint.facets:
            if issubclass(facet, AttackFacet):
                self.attacks.append(facet(self))
            elif issubclass(facet, ActivatedAbilityFacet):
                self.activated_abilities.append(facet(self))
            elif issubclass(facet, StaticAbilityFacet):
                self.static_abilities.append(facet(self))

        for facet in self.attacks + self.activated_abilities + self.static_abilities:
            facet.create_effects()

    def get_primary_attack(self, of_type: type[C] | None = None) -> C | None:
        for attack in self.attacks:
            if of_type is None or isinstance(attack, of_type):
                return attack
        return None

    @modifiable
    def get_resistance_against(self, signature: DamageSignature) -> Resistance:
        return Resistance.NONE

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return GS.map.hex_off(self).get_terrain_protection_for(request)

    def suffer_damage(self, signature: DamageSignature) -> int:
        damage = min(
            signature.amount, self.health - 1 if not signature.lethal else self.health
        )
        self.damage += damage
        return damage

    @modifiable
    def can_be_activated(self, _: None = None) -> bool:
        return not self.exhausted

    @modifiable
    def can_be_attacked_by(self, attack: AttackFacet) -> bool:
        return True

    @modifiable
    def blocks_vision_for(self, player: Player) -> bool:
        size = self.size.g()
        if size == Size.LARGE:
            return True
        if size == Size.SMALL:
            return False
        return player != self.controller

    @modifiable
    def provides_vision_for(self, _: None) -> set[Player]:
        return {self.controller}

    @modifiable
    def can_see(self, space: Hex) -> bool:
        if space.map.distance_between(self, space) > self.sight.g():
            return False
        return not line_of_sight_obstructed_for_unit(
            self, space.map.position_off(self), space.position
        )

    @modifiable
    def is_hidden_for(self, player: Player) -> bool:
        return False

    @modifiable
    def is_visible_to(self, player: Player) -> bool:
        return (
            player == self.controller or GS.map.hex_off(self).is_visible_to(player)
        ) and not self.is_hidden_for(player)

    # TODO should effects modifying get_legal_options on movement modify this instead?
    @modifiable
    def get_potential_move_destinations(self, _: None) -> list[Hex]:
        return [
            _hex
            for _hex in GS.map.get_neighbors_off(self)
            if not _hex.is_visible_to(self.controller) or _hex.can_move_into(self)
        ]

    @modifiable
    def get_legal_options(self, context: ActiveUnitContext) -> list[Option]:
        options = []
        if context.movement_points > 0:
            if moveable_hexes := [
                h
                for h in self.get_potential_move_destinations(None)
                if not context.has_acted
                or h.get_move_in_cost_for(self) <= context.movement_points
            ]:
                options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))
        if context.movement_points >= 0:
            for facet in self.attacks:
                if isinstance(
                    facet, (MeleeAttackFacet, RangedAttackFacet)
                ) and facet.can_be_activated(context):
                    options.append(
                        EffortOption(
                            facet,
                            target_profile=OneOfUnits(facet.get_legal_targets(context)),
                        )
                    )
            for facet in self.activated_abilities:
                if facet.can_be_activated(context):
                    options.append(
                        EffortOption(facet, target_profile=facet.get_target_profile())
                    )
        if not context.has_acted or options:
            options.append(SkipOption(target_profile=NoTarget()))
        return options

    # TODO alive?
    def on_map(self) -> bool:
        return self in GS.map.unit_positions

    @property
    def health(self) -> int:
        return self.max_health.g() - self.damage

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "blueprint": self.blueprint.identifier,
            "controller": self.controller.name,
            "max_health": self.max_health.g(),
            "damage": self.damage,
            "speed": self.speed.g(),
            "sight": self.sight.g(),
            "max_energy": self.max_energy.g(),
            "energy": self.energy,
            # TODO
            "size": self.size.g().name[0],
            "armor": self.armor.g(),
            "attack_power": self.attack_power.g(),
            "exhausted": self.exhausted,
            "is_ghost": False,
            "statuses": [
                status.serialize(context)
                for status in self.statuses
                if not status.is_hidden_for(context.player)
            ],
        }

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.blueprint.name}, {self.controller.name}, {id(self)})"


class UnitStatus(Status[Unit], ABC):
    category: ClassVar[str] = "unit"
    default_intention: ClassVar[StatusIntention | None] = None

    def __init__(
        self,
        *,
        controller: Player | None = None,
        source: Source = None,
        duration: int | None = None,
        stacks: int | None = None,
        parent: H | None,
        intention: StatusIntention,
    ):
        super().__init__(
            controller=controller,
            source=source,
            duration=duration,
            stacks=stacks,
            parent=parent,
        )
        self.intention = intention

    @classmethod
    def get(cls, identifier: str) -> type[UnitStatus]:
        return cls.registry[identifier]

    def serialize(self, context: SerializationContext) -> JSON:
        return {**super().serialize(context), "intention": self.intention.value}


@dataclasses.dataclass
class StatusSignature:
    status_type: type[UnitStatus]
    source: Source
    stacks: int | None = None
    duration: int | None = None
    intention: StatusIntention | None = None


@dataclasses.dataclass
class OneOfUnits(TargetProfile[Unit]):
    units: list[Unit]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.units]
        }

    def parse_response(self, v: Any) -> Unit:
        return self.units[v["index"]]


@dataclasses.dataclass
class NOfUnits(TargetProfile[list[Unit]]):
    units: list[Unit]
    select_count: int
    labels: list[str]
    min_count: int | None = None

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.units],
            "select_count": self.select_count,
            "min_count": self.min_count,
            "labels": self.labels,
        }

    def parse_response(self, v: Any) -> list[Unit]:
        indexes = v["indexes"]
        # TODO nice validation LMAO
        # assert len(indexes) == self.select_count
        # assert len(indexes) == len(set(indexes))
        return [self.units[idx] for idx in indexes]


class DurationStatusMixin:
    duration: int | None

    def merge(self, incoming: Self) -> bool:
        if (
            incoming.duration is None
            or self.duration is None
            or (incoming.duration > self.duration)
        ):
            self.duration = incoming.duration
        return True


# TODO ABC, where should this be?
# TODO just use the mixin instead
class RefreshableDurationUnitStatus(DurationStatusMixin, UnitStatus, ABC): ...


class NoTargetActivatedAbility(ActivatedAbilityFacet[None], ABC):
    def get_target_profile(self) -> TargetProfile[None] | None:
        return NoTarget()


class SingleTargetActivatedAbility(ActivatedAbilityFacet[Unit], ABC):
    range: ClassVar[int] = 1
    requires_los: ClassVar[bool] = True

    def can_target_unit(self, unit: Unit) -> bool:
        return True

    def get_target_profile(self) -> TargetProfile[Unit] | None:
        if units := [
            unit
            for unit in GS.map.get_units_within_range_off(self.owner, self.range)
            if self.can_target_unit(unit)
            and unit.is_visible_to(self.owner.controller)
            and (
                not self.requires_los
                or not line_of_sight_obstructed_for_unit(
                    self.owner,
                    GS.map.position_off(self.owner),
                    GS.map.position_off(unit),
                )
            )
        ]:
            return OneOfUnits(units)


class SingleAllyActivatedAbility(SingleTargetActivatedAbility, ABC):
    can_target_self: ClassVar[bool] = True

    def can_target_unit(self, unit: Unit) -> bool:
        return unit.controller == self.owner.controller and (
            self.can_target_self or unit != self.owner
        )


class SingleEnemyActivatedAbility(SingleTargetActivatedAbility, ABC):

    def can_target_unit(self, unit: Unit) -> bool:
        return unit.controller != self.owner.controller


@dataclasses.dataclass
class HexSpec:
    terrain_type: type[Terrain]
    is_objective: bool
    statuses: list[HexStatusSignature] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Landscape:
    terrain_map: Mapping[CC, HexSpec]
    # deployment_zones: Collection[AbstractSet[CubeCoordinate]]


@dataclasses.dataclass
class Scenario:
    landscape: Landscape
    units: list[Mapping[CC, UnitBlueprint]]


@dataclasses.dataclass
class TerrainProtectionRequest:
    unit: Unit
    damage_signature: DamageSignature


class Terrain(HasEffects, Registered, ABC, metaclass=get_registered_meta()):
    registry: dict[str, type[Terrain]]
    is_water: ClassVar[bool] = False
    blocks_vision: ClassVar[bool] = False
    is_high_ground: ClassVar[bool] = False

    def create_effects(self, space: Hex) -> None: ...

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return 0

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "description": cls.description,
            "related_statuses": cls.related_statuses,
            "is_water": cls.is_water,
            "is_high_ground": cls.is_high_ground,
            "blocks_vision": cls.blocks_vision,
        }


@dataclasses.dataclass
class Hex(Modifiable, HasStatuses, Serializable):
    position: CC
    terrain: Terrain
    is_objective: bool
    map: HexMap

    @modifiable
    def is_passable_to(self, unit: Unit) -> bool:
        if self.terrain.is_water:
            return unit.aquatic.g()
        return True

    @modifiable
    def is_occupied_for(self, unit: Unit) -> bool:
        # TODO should prob be inverted?
        return not self.map.unit_on(self)

    @modifiable
    def can_move_into(self, unit: Unit) -> bool:
        return self.is_occupied_for(unit) and self.is_passable_to(unit)

    @modifiable
    def get_move_in_cost_for(self, unit: Unit) -> int:
        if (
            self.terrain.is_high_ground
            and not GS.map.hex_off(unit).terrain.is_high_ground
        ):
            return 2
        return 1

    @modifiable
    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_in_penalty_for(unit)

    @modifiable
    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_out_penalty_for(unit)

    @modifiable
    def blocks_vision_for(self, player: Player) -> VisionObstruction:
        if self.terrain.blocks_vision:
            if self.terrain.is_high_ground:
                return VisionObstruction.FULL
            return VisionObstruction.FOR_LOW_GROUND
        if (unit := self.map.unit_on(self)) and unit.blocks_vision_for(player):
            if self.terrain.is_high_ground:
                return VisionObstruction.FULL
            return VisionObstruction.FOR_LOW_GROUND
        if self.terrain.is_high_ground:
            return VisionObstruction.FOR_LOW_GROUND
        return VisionObstruction.NONE

    @modifiable
    def is_visible_to(self, player: Player) -> bool:
        return GS.vision_map[player][self.position]

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return self.terrain.get_terrain_protection_for(request) + (
            1
            if request.damage_signature.type
            in (DamageType.RANGED, DamageType.MELEE, DamageType.AOE)
            and isinstance(request.damage_signature.source, Facet)
            and GS.map.hex_off(request.unit).terrain.is_high_ground
            and not GS.map.hex_off(
                request.damage_signature.source.owner
            ).terrain.is_high_ground
            else 0
        )

    def serialize(self, context: SerializationContext) -> JSON:
        old_hex = (context.last_hex_states or {}).get(self.position)
        return {
            "cc": self.position.serialize(),
            "terrain": self.terrain.__class__.identifier,
            "is_objective": self.is_objective,
            **(
                {
                    "visible": True,
                    "last_visible_round": GS.round_counter,
                    "unit": (
                        unit.serialize(context)
                        if (unit := self.map.unit_on(self))
                        and unit.is_visible_to(context.player)
                        else (
                            old_hex["unit"] | {"is_ghost": True}
                            if old_hex
                            and old_hex["unit"]
                            and old_hex["unit"]["id"] not in context.visible_unit_ids
                            else None
                        )
                    ),
                    "statuses": [
                        status.serialize(context)
                        for status in self.statuses
                        if not status.is_hidden_for(context.player)
                    ],
                }
                if self.is_visible_to(context.player)
                else (
                    {
                        "visible": False,
                        "last_visible_round": old_hex["last_visible_round"],
                        "unit": (
                            old_hex["unit"] | {"is_ghost": True}
                            if old_hex["unit"]
                            and old_hex["unit"]["id"] not in context.visible_unit_ids
                            else None
                        ),
                        "statuses": old_hex["statuses"],
                    }
                    if old_hex
                    else {
                        "visible": False,
                        "last_visible_round": None,
                        "unit": None,
                        "statuses": [],
                    }
                )
            ),
        }

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self):
        return f"{type(self).__name__}({self.position.r}, {self.position.h})"


Source: TypeAlias = Facet | Status | None


@dataclasses.dataclass
class DamageSignature:
    amount: int
    source: Source
    type: DamageType = DamageType.PHYSICAL
    ap: int = 0
    lethal: bool = True

    def branch(self, **kwargs: Any) -> DamageSignature:
        return type(self)(
            **{
                field.name: getattr(self, field.name)
                for field in dataclasses.fields(self)
            }
            | kwargs
        )

    def with_damage(self, amount: int) -> DamageSignature:
        return self.branch(amount=amount)


class HexStatus(Status[Hex], ABC):
    category: ClassVar[str] = "hex"

    # TODO obsolete?
    @classmethod
    def get(cls, identifier: str) -> type[HexStatus]:
        return cls.registry[identifier]


# TODO inherit from status signature base?
@dataclasses.dataclass
class HexStatusSignature:
    status_type: type[HexStatus]
    source: Source
    stacks: int | None = None
    duration: int | None = None


class SingleHexTargetActivatedAbility(ActivatedAbilityFacet[Hex], ABC):
    range: ClassVar[int] = 1
    requires_los: ClassVar[bool] = True
    requires_vision: ClassVar[bool] = True

    def can_target_hex(self, hex_: Hex) -> bool:
        return True

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := [
            _hex
            for _hex in GS.map.get_hexes_within_range_off(self.owner, self.range)
            if (not self.requires_vision or _hex.is_visible_to(self.owner.controller))
            and (
                not self.requires_los
                or not line_of_sight_obstructed_for_unit(
                    self.owner,
                    GS.map.position_off(self.owner),
                    _hex.position,
                )
            )
            and self.can_target_hex(_hex)
        ]:
            return OneOfHexes(hexes)


@dataclasses.dataclass
class OneOfHexes(TargetProfile[Hex]):
    hexes: list[Hex]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"options": [_hex.position.serialize() for _hex in self.hexes]}

    def parse_response(self, v: Any) -> Hex:
        return self.hexes[v["index"]]


# TODO where, maybe in "aoe_target_profiles.py"?
@dataclasses.dataclass
class ConsecutiveAdjacentHexes(TargetProfile[list[Hex]]):
    adjacent_to: Hex
    arm_length: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "adjacent_to": self.adjacent_to.position.serialize(),
            "arm_length": self.arm_length,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        return list(
            GS.map.get_hexes_of_positions(
                hex_arc(
                    radius=1,
                    arm_length=self.arm_length,
                    stroke_center=CC(**v["cc"]),
                    arc_center=self.adjacent_to.position,
                )
            )
        )


# TODO terrible name
@dataclasses.dataclass
class HexHexes(TargetProfile[list[Hex]]):
    centers: list[Hex]
    radius: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "centers": [_hex.position.serialize() for _hex in self.centers],
            "radius": self.radius,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        return list(
            GS.map.get_hexes_within_range_off(self.centers[v["index"]], self.radius)
        )


@dataclasses.dataclass
class TriHex(TargetProfile[list[Hex]]):
    corners: list[Corner]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "corners": [corner.serialize() for corner in self.corners],
        }

    def parse_response(self, v: Any) -> list[Hex]:
        return list(
            GS.map.get_hexes_of_positions(
                self.corners[v["index"]].get_adjacent_positions()
            )
        )


@dataclasses.dataclass
class HexRing(TargetProfile[list[Hex]]):
    centers: list[Hex]
    radius: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "centers": [_hex.position.serialize() for _hex in self.centers],
            "radius": self.radius,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        return list(
            GS.map.get_hexes_of_positions(
                hex_ring(self.radius, self.centers[v["index"]].position)
            )
        )


@dataclasses.dataclass
class RadiatingLine(TargetProfile[list[Hex]]):
    from_hex: Hex
    to_hexes: list[Hex]
    length: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "from_hex": self.from_hex.position.serialize(),
            "to_hexes": [h.position.serialize() for h in self.to_hexes],
            "length": self.length,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        selected_cc = self.to_hexes[v["index"]].position
        difference = selected_cc - self.from_hex.position
        return [
            projected
            for i in range(self.length)
            if (projected := GS.map.hexes.get(selected_cc + difference * i))
        ]


@dataclasses.dataclass
class Cone(TargetProfile[list[Hex]]):
    from_hex: Hex
    to_hexes: list[Hex]
    arm_lengths: list[int]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "from_hex": self.from_hex.position.serialize(),
            "to_hexes": [h.position.serialize() for h in self.to_hexes],
            "arm_lengths": self.arm_lengths,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        selected_cc = self.to_hexes[v["index"]].position
        difference = selected_cc - self.from_hex.position
        return list(
            GS.map.get_hexes_of_positions(
                itertools.chain(
                    *(
                        hex_arc(
                            idx + 1,
                            arm_length=arm_length,
                            stroke_center=selected_cc + difference * idx,
                            arc_center=self.from_hex.position,
                        )
                        for idx, arm_length in enumerate(self.arm_lengths)
                    )
                )
            )
        )


@dataclasses.dataclass
class TreeNode:
    options: list[tuple[Unit | Hex, TreeNode | None]]
    label: str

    @classmethod
    def serialize_option(
        cls, option: Unit | Hex, context: SerializationContext
    ) -> JSON:
        if isinstance(option, Unit):
            return {"type": "unit", "id": context.id_map.get_id_for(option)}
        return {"type": "hex", "cc": option.position.serialize()}

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "label": self.label,
            "options": [
                (
                    self.serialize_option(game_object, context),
                    sub_tree.serialize(context) if sub_tree else None,
                )
                for game_object, sub_tree in self.options
            ],
        }


@dataclasses.dataclass
class Tree(TargetProfile[list[Unit | Hex]]):
    root_node: TreeNode

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"root_node": self.root_node.serialize(context)}

    def parse_response(self, v: Any) -> list[Unit | Hex]:
        indexes = v["indexes"]
        selected = []
        current = self.root_node
        for idx in indexes:
            obj, node = current.options[idx]
            selected.append(obj)
            current = node
        return selected


class MovementException(Exception): ...


CCArg: TypeAlias = CC | Hex | Unit


# TODO reasonable and consistent utils interface for this disaster
class HexMap:
    def __init__(self, landscape: Landscape):
        # TODO all these should be private
        self.hexes = {
            position: Hex(
                position=position,
                terrain=hex_spec.terrain_type(),
                is_objective=hex_spec.is_objective,
                map=self,
            )
            for position, hex_spec in landscape.terrain_map.items()
        }
        for _hex in self.hexes.values():
            _hex.terrain.create_effects(_hex)
        self.unit_positions: bidict[Unit, Hex] = bidict()
        # TODO better plan for handling this
        self.last_known_positions: dict[Unit, Hex] = {}

    @property
    def units(self) -> list[Unit]:
        return list(self.unit_positions.keys())

    def units_controlled_by(self, player: Player) -> Iterator[Unit]:
        for unit in self.units:
            if unit.controller == player:
                yield unit

    def hex_off(self, unit: Unit) -> Hex:
        return self.unit_positions.get(unit) or self.last_known_positions[unit]

    def position_off(self, unit: Unit) -> CC:
        return self.hex_off(unit).position

    def _to_cc(self, value: CCArg) -> CC:
        if isinstance(value, Hex):
            return value.position
        if isinstance(value, Unit):
            return self.hex_off(value).position
        return value

    def _to_hex(self, value: CCArg) -> Hex:
        if isinstance(value, CC):
            return self.hexes[value]
        if isinstance(value, Unit):
            return self.hex_off(value)
        return value

    def move_unit_to(self, unit: Unit, to: CCArg) -> None:
        _hex = self._to_hex(to)
        if self.unit_positions.inverse.get(_hex) is not None:
            raise MovementException()
        self.unit_positions[unit] = _hex

    def remove_unit(self, unit: Unit) -> None:
        self.last_known_positions[unit] = self.unit_positions[unit]
        del self.unit_positions[unit]

    def unit_on(self, on: CCArg) -> Unit | None:
        return self.unit_positions.inverse.get(self._to_hex(on))

    def units_on(self, on: Iterable[CCArg]) -> Iterator[Unit]:
        for o in on:
            if unit := self.unit_on(o):
                yield unit

    def distance_between(self, from_: CCArg, to_: CCArg) -> int:
        return self._to_cc(from_).distance_to(self._to_cc(to_))

    def get_neighbors_off(self, off: CCArg) -> Iterator[Hex]:
        for neighbor_coordinate in self._to_cc(off).neighbors():
            if _hex := self.hexes.get(neighbor_coordinate):
                yield _hex

    def get_neighboring_units_off(
        self, off: CCArg, controlled_by: Player | None = None
    ) -> Iterator[Unit]:
        for _hex in self.get_neighbors_off(off):
            if unit := self.unit_positions.inverse.get(_hex):
                if controlled_by is None or controlled_by == unit.controller:
                    yield unit

    def get_hexes_within_range_off(self, off: CCArg, distance: int) -> Iterator[Hex]:
        for cc in hex_circle(distance, center=self._to_cc(off)):
            if cc in self.hexes:
                yield self.hexes[cc]

    def get_corners_within_range_off(
        self, off: CCArg, distance: int
    ) -> Iterator[Corner]:
        for cc in hex_circle(distance, center=(center := self._to_cc(off))):
            for position in CornerPosition:
                corner = Corner(cc, position)
                if all(
                    cc in self.hexes and cc.distance_to(center) <= distance
                    for cc in corner.get_adjacent_positions()
                ):
                    yield corner

    def get_units_within_range_off(self, off: CCArg, distance: int) -> Iterator[Unit]:
        for _hex in self.get_hexes_within_range_off(off, distance):
            if unit := self.unit_positions.inverse.get(_hex):
                yield unit

    def get_hexes_of_positions(self, positions: Iterable[CC]) -> Iterator[Hex]:
        for position in positions:
            if position in self.hexes:
                yield self.hexes[position]

    def serialize(self, context: SerializationContext) -> JSON:
        return {"hexes": [_hex.serialize(context) for _hex in self.hexes.values()]}


@dataclasses.dataclass
class ActiveUnitContext(Serializable):
    unit: Unit
    movement_points: int
    has_acted: bool = False
    should_stop: bool = False
    activated_facets: defaultdict[str, int] = dataclasses.field(
        default_factory=lambda: defaultdict(int)
    )
    locked_into: EffortFacet | None = None

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "unit": self.unit.serialize(context),
            "movement_points": self.movement_points,
        }


@dataclasses.dataclass
class LogLine:
    elements: list[str | Unit | Hex | list[Hex | Unit] | EffortFacet | Status]

    def is_visible_to(self, player: Player) -> bool:
        for element in self.elements:
            if isinstance(element, list) and not any(
                e.is_visible_to(player) for e in element
            ):
                return False
            if isinstance(element, Unit) and not element.is_visible_to(player):
                return False
            if isinstance(element, Hex) and not element.is_visible_to(player):
                return False
            if isinstance(element, Status) and element.is_hidden_for(player):
                return False
        return True

    @classmethod
    def _serialize_element(
        cls, element: str | Unit | Hex, player: Player, id_map: IDMap
    ) -> dict[str, Any]:
        if isinstance(element, Unit):
            return {
                "type": "unit",
                "identifier": id_map.get_id_for(element),
                "blueprint": element.blueprint.identifier,
                "controller": element.controller.name,
            }
        if isinstance(element, Hex):
            return {"type": "hex", "cc": element.position.serialize()}
        if isinstance(element, EffortFacet):
            return {"type": "facet", "identifier": element.identifier}
        if isinstance(element, Status):
            return {"type": "status", "identifier": element.identifier}
        if isinstance(element, list):
            return {
                "type": "list",
                "items": [
                    cls._serialize_element(e, player, id_map)
                    for e in element
                    if e.is_visible_to(player)
                ],
            }
        return {"type": "string", "message": element}

    def serialize(self, player: Player, id_map: IDMap) -> list[dict[str, Any]]:
        return [
            self._serialize_element(element, player, id_map)
            for element in self.elements
        ]


class GameState:
    instance: GameState | None = None

    def __init__(
        self,
        player_count: int,
        connection_factory: Callable[[Player], Connection],
        landscape: Landscape,
    ):
        # TODO handle names
        self.turn_order = TurnOrder(
            [Player(f"player {i+1}") for i in range(player_count)]
        )
        self.connections = {
            player: connection_factory(player) for player in self.turn_order.players
        }
        self.map = HexMap(landscape)
        self.active_unit_context: ActiveUnitContext | None = None
        self.activation_queued_units: set[Unit] = set()
        self.target_points = 23
        self.round_counter = 0

        # TODO move to player
        self.id_maps: dict[Player, IDMap] = {
            player: IDMap() for player in self.turn_order.players
        }
        self.previous_hex_states: dict[Player, dict[CC, dict[str, Any]] | None] = {
            player: None for player in self.turn_order.players
        }

        self.vision_obstruction_map: dict[Player, dict[CC, VisionObstruction]] = {}
        self.vision_map: dict[Player, dict[CC, bool]] = {}

        # TODO move to player
        self._player_log_levels: dict[Player, int] = {
            player: 0 for player in self.turn_order.players
        }
        self._pending_player_logs: dict[
            Player, list[tuple[int, list[dict[str, Any]]]]
        ] = {player: [] for player in self.turn_order.players}

    @contextlib.contextmanager
    def log(self, *line_options: LogLine) -> Iterator[None]:
        incremented_players = []
        for player in self.turn_order.players:
            for line in line_options:
                if line.is_visible_to(player):
                    incremented_players.append(player)
                    self._pending_player_logs[player].append(
                        (
                            self._player_log_levels[player],
                            line.serialize(player, self.id_maps[player]),
                        )
                    )
                    self._player_log_levels[player] += 1
                    break
        yield
        for player in incremented_players:
            self._player_log_levels[player] -= 1

    def update_vision(self) -> None:
        unit_vision_map: dict[player, list[Unit]] = defaultdict(list)
        for unit in self.map.unit_positions.keys():
            for player in unit.provides_vision_for(None):
                unit_vision_map[player].append(unit)

        for player in self.turn_order.players:
            self.vision_obstruction_map[player] = {
                position: _hex.blocks_vision_for(player)
                for position, _hex in self.map.hexes.items()
            }

        for player in self.turn_order.players:
            self.vision_map[player] = {
                position: any(unit.can_see(_hex) for unit in unit_vision_map[player])
                for position, _hex in self.map.hexes.items()
            }

    def serialize_for(
        self, context: SerializationContext, decision_point: DecisionPoint | None
    ) -> Mapping[str, Any]:
        serialized_game_state = {
            "player": context.player.name,
            "target_points": self.target_points,
            "players": [player.serialize() for player in self.turn_order.players],
            "round": self.round_counter,
            "map": self.map.serialize(context),
            "decision": decision_point.serialize(context) if decision_point else None,
            "active_unit_context": (
                self.active_unit_context.serialize(context)
                if self.active_unit_context
                and self.active_unit_context.unit.is_visible_to(context.player)
                else None
            ),
            "logs": self._pending_player_logs[context.player],
        }
        # TODO yikes
        self.previous_hex_states[context.player] = {
            CC(**hex_values["cc"]): hex_values
            for hex_values in serialized_game_state["map"]["hexes"]
        }
        # TODO lmao
        context.id_map.prune()
        return serialized_game_state

    def _get_context_for(self, player: Player) -> SerializationContext:
        return SerializationContext(
            player,
            self.id_maps[player],
            self.previous_hex_states[player],
            visible_unit_ids={
                self.id_maps[player].get_id_for(unit)
                for unit in self.map.units
                if unit.is_visible_to(player)
            },
        )

    def update_ghosts(self) -> None:
        for player in self.turn_order.players:
            self.serialize_for(self._get_context_for(player), None)

    def send_to_players(self) -> None:
        for _player in self.turn_order.players:
            self.connections[_player].send(
                self.serialize_for(self._get_context_for(_player), None)
            )

    def make_decision(self, player: Player, decision_point: DecisionPoint[O]) -> O:
        for _player in self.turn_order.players:
            if _player != player:
                self.connections[_player].send(
                    self.serialize_for(self._get_context_for(_player), None)
                )
        response = self.connections[player].get_response(
            self.serialize_for(self._get_context_for(player), decision_point)
        )
        return decision_point.parse_response(response)


class ScopedGameState:

    # TODO protocol/interface?
    def __init__(self):
        self._store = threading.local()

    def bind(self, gs: GameState) -> None:
        self._store.value = gs

    @property
    def _gs(self) -> GameState:
        return self._store.value

    @property
    def turn_order(self) -> TurnOrder:
        return self._gs.turn_order

    @property
    def connections(self) -> dict[Player, Connection]:
        return self._gs.connections

    @property
    def map(self) -> HexMap:
        return self._gs.map

    @property
    def active_unit_context(self) -> ActiveUnitContext | None:
        return self._gs.active_unit_context

    @active_unit_context.setter
    def active_unit_context(self, v: ActiveUnitContext) -> None:
        self._gs.active_unit_context = v

    @property
    def activation_queued_units(self) -> set[Unit]:
        return self._gs.activation_queued_units

    @property
    def target_points(self) -> int:
        return self._gs.target_points

    @property
    def round_counter(self) -> int:
        return self._gs.round_counter

    @round_counter.setter
    def round_counter(self, v: int) -> None:
        self._gs.round_counter = v

    @property
    def id_maps(self) -> dict[Player, IDMap]:
        return self._gs.id_maps

    @property
    def previous_hex_states(self) -> dict[Player, dict[CC, dict[str, Any]]]:
        return self._gs.previous_hex_states

    @property
    def vision_obstruction_map(self) -> dict[Player, dict[CC, VisionObstruction]]:
        return self._gs.vision_obstruction_map

    @property
    def vision_map(self) -> dict[Player, dict[CC, bool]]:
        return self._gs.vision_map

    # TODO pretty dumb
    @contextlib.contextmanager
    def log(self, *line_options: LogLine) -> Iterator[None]:
        with self._gs.log(*line_options):
            yield None

    def update_vision(self) -> None:
        self._gs.update_vision()

    def serialize_for(
        self, context: SerializationContext, decision_point: DecisionPoint | None
    ) -> Mapping[str, Any]:
        return self._gs.serialize_for(context, decision_point)

    def update_ghosts(self) -> None:
        self._gs.update_ghosts()

    def send_to_players(self) -> None:
        self._gs.send_to_players()

    def make_decision(self, player: Player, decision_point: DecisionPoint[O]) -> O:
        return self._gs.make_decision(player, decision_point)


GS = ScopedGameState()
