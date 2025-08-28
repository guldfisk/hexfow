from game.core import CohesiveGroupMixin, HexStatusLink, LooseGroupMixin, UnitStatusLink
from game.effects.replacements import GateReplacement
from game.effects.triggers import TaintedBondTrigger


class GateLink(CohesiveGroupMixin, HexStatusLink):
    def create_effects(self) -> None:
        self.register_effects(GateReplacement(self))


class TaintedLink(LooseGroupMixin, UnitStatusLink):
    def create_effects(self) -> None:
        self.register_effects(TaintedBondTrigger(self))
