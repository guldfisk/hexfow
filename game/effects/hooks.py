import dataclasses

from events.eventsystem import Event, HookEffect
from game.core import GS, Unit
from game.events import TurnUpkeep


@dataclasses.dataclass(eq=False)
class AdjacencyHook(HookEffect[TurnUpkeep]):
    unit: Unit
    adjacent_units: list[Unit] = dataclasses.field(default_factory=list)

    def resolve_hook_call(self, event: Event):
        self.adjacent_units = list(GS.map.get_neighboring_units_off(self.unit))
