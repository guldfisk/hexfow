from __future__ import annotations

import dataclasses
from typing import ClassVar

from events.eventsystem import Modifiable, ModifiableAttribute
from game.game.player import Player
from game.game.statuses import HasStatuses
from game.game.values import Size


class Facet(HasStatuses):
    name: ClassVar[str]

    def __init__(self, owner: Unit):
        self.owner = owner

    def create_effects(self) -> None: ...


class EffortFacet(Facet): ...


class AttackFacet(EffortFacet): ...


class ActivatedAbilityFacet(EffortFacet): ...


class StatickAbilityFacet(Facet): ...


@dataclasses.dataclass
class UnitBlueprint:
    name: str
    health: int
    speed: int
    sight: int
    energy: int = 0
    size: Size = Size.MEDIUM
    facets: list[type[Facet]] = dataclasses.field(default_factory=list)


class Unit(Modifiable, HasStatuses):
    speed: ModifiableAttribute[None, int]
    sight: ModifiableAttribute[None, int]
    max_health: ModifiableAttribute[None, int]
    max_energy: ModifiableAttribute[None, int]
    size: ModifiableAttribute[None, Size]
    attack_power: ModifiableAttribute[None, int]

    def __init__(self, controller: Player, blueprint: UnitBlueprint):
        self.controller = controller
        self.blueprint = blueprint

        self.health = blueprint.health
        self.max_health.set(blueprint.health)
        self.sight.set(blueprint.sight)
        self.energy: int = blueprint.energy
        self.max_energy.set(blueprint.energy)
        self.size.set(blueprint.size)
        self.attack_power.set(0)

        self.attacks: list[AttackFacet] = []
        self.activated_abilities: list[ActivatedAbilityFacet] = []
        self.static_abilities: list[StatickAbilityFacet] = []

        for facet in blueprint.facets:
            if issubclass(facet, AttackFacet):
                self.attacks.append(facet(self))
            elif issubclass(facet, ActivatedAbilityFacet):
                self.activated_abilities.append(facet(self))
            elif issubclass(facet, StatickAbilityFacet):
                self.static_abilities.append(facet(self))

        for facet in self.attacks + self.activated_abilities + self.static_abilities:
            facet.create_effects()
