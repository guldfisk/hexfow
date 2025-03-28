import dataclasses

from events.eventsystem import Event, V, ES
from game.game.game import GM
from game.game.map.hexmap import Hex
from game.game.player import Player
from game.game.units.facets.attacks import MeleeAttackFacet
from game.game.units.unit import Unit, UnitBlueprint, Facet


@dataclasses.dataclass
class Damage(Event[None]):
    unit: Unit
    amount: int

    def resolve(self) -> None:
        self.unit.health -= self.amount


@dataclasses.dataclass
class MeleeAttack(Event[None]):
    attacker: Unit
    defender: Unit
    attack: MeleeAttackFacet

    def resolve(self) -> None:
        ES.resolve(Damage(self.defender, self.attack.damage))
        # self.defender.health -= self.attack.damage


@dataclasses.dataclass
class SpawnUnit(Event[Unit | None]):
    blueprint: UnitBlueprint
    controller: Player
    space: Hex

    def resolve(self) -> Unit | None:
        if GM().map.unit_on(self.space):
            return None
        unit = Unit(self.controller, self.blueprint)
        GM().map.move_unit_to(unit)
        return unit


@dataclasses.dataclass
class MoveUnit(Event[Hex | None]):
    unit: Unit
    to_: Hex

    def resolve(self) -> Hex | None:
        if GM().map.unit_on(self.to_):
            return None
        from_ = GM().map.position_of(self.unit)
        GM().map.move_unit_to(self.unit, self.to_)
        return from_
