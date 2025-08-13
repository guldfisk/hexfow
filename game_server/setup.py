import dataclasses
from typing import Callable, ClassVar

from events.eventsystem import ES, EventSystem, StateModifierEffect
from game.core import GameState, GS, Hex, Unit, Scenario
from game.events import SpawnUnit, ApplyHexStatus
from game.interface import Connection
from game.player import Player


def setup_scenario(
    scenario: Scenario,
    connection_factory: Callable[[Player], Connection],
    with_fow: bool = True,
) -> GameState:
    ES.bind(EventSystem())

    gs = GameState(2, connection_factory, scenario.landscape)

    GS.bind(gs)

    for player, units in zip(gs.turn_order, scenario.units):
        for cc, blueprint in units.items():
            ES.resolve(
                SpawnUnit(
                    blueprint=blueprint,
                    controller=player,
                    space=gs.map.hexes[cc],
                )
            )

    for cc, spec in scenario.landscape.terrain_map.items():
        for signature in spec.statuses:
            ES.resolve(ApplyHexStatus(gs.map.hexes[cc], signature))

    @dataclasses.dataclass(eq=False)
    class AllHexRevealedModifier(StateModifierEffect[Hex, Player, bool]):
        priority: ClassVar[int] = 100
        target: ClassVar[object] = Hex.is_visible_to

        def modify(self, obj: Hex, request: Player, value: bool) -> bool:
            return True

    @dataclasses.dataclass(eq=False)
    class AllUnitsRevealedModifier(StateModifierEffect[Hex, Player, bool]):
        priority: ClassVar[int] = 100
        target: ClassVar[object] = Unit.is_hidden_for

        def modify(self, obj: Unit, request: Player, value: bool) -> bool:
            return False

    effects = [AllHexRevealedModifier(), AllUnitsRevealedModifier()]

    ES.register_effects(*effects)

    for player in gs.turn_order:
        gs.serialize_for(gs._get_context_for(player), None)

    if with_fow:
        ES.deregister_effects(*effects)

    for logs in gs._pending_player_logs.values():
        logs[:] = []

    return gs
