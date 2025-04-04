from abc import ABC

from game.game.decisions import DecisionPoint, O


class Interface(ABC):

    def make_decision(self, decision: DecisionPoint[O]) -> O:
        ...
