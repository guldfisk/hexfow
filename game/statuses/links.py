from game.core import CohesiveGroupMixin, HexStatusLink
from game.effects.replacements import GateReplacement


class GateLink(CohesiveGroupMixin, HexStatusLink):
    def create_effects(self) -> None:
        self.register_effects(GateReplacement(self))
