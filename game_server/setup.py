import dataclasses
from typing import Callable, ClassVar

from events.eventsystem import ES, EventSystem, StateModifierEffect
from game.core import GS, Connection, GameState, Hex, Player, Scenario, Unit
from game.events import ApplyHexStatus, DeployArmies, SpawnUnit


def setup_scenario(
    scenario: Scenario,
    connection_factory: Callable[[Player], Connection],
) -> GameState:
    ES.bind(EventSystem())

    gs = GameState(
        player_count=2, connection_factory=connection_factory, scenario=scenario
    )

    GS.bind(gs)

    return gs


def setup_scenario_units(
    scenario: Scenario,
    with_fow: bool = True,
    custom_armies: bool = False,
) -> GameState:
    gs = GS._gs
    if custom_armies:
        ES.resolve(DeployArmies(scenario))
    else:
        for player, units in zip(gs.turn_order, scenario.units):
            for cc, blueprint in units.items():
                ES.resolve(
                    SpawnUnit(
                        blueprint=blueprint,
                        controller=player,
                        space=gs.map.hexes[cc],
                        setup=True,
                    )
                )

    for cc, spec in scenario.landscape.terrain_map.items():
        for signature in spec.statuses:
            ES.resolve(ApplyHexStatus(gs.map.hexes[cc], signature))

    if not with_fow or not custom_armies:

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

        gs.update_vision()
        gs.update_ghosts()

        if with_fow:
            ES.deregister_effects(*effects)

    return gs
