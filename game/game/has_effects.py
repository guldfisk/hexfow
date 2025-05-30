import dataclasses

from events.eventsystem import Effect, ES


@dataclasses.dataclass
class HasEffects:
    effects: set[Effect] = dataclasses.field(default_factory=set, init=False)

    def register_effects(self, *effects: Effect) -> None:
        self.effects.update(effects)
        ES.register_effects(*effects)

    def deregister_effects(self, *effects: Effect) -> None:
        for effect in effects:
            self.effects.discard(effect)
        ES.deregister_effects(*effects)

    def deregister(self) -> None:
        ES.deregister_effects(*self.effects)
        self.effects = set()
