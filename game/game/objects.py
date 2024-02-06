import dataclasses

from events.eventsystem import Effect


@dataclasses.dataclass
class GameObject:
    effects: list[Effect] = dataclasses.field(default_factory=list)
