# import dataclasses
# from abc import ABC
# from typing import TypeVar, Generic
#
# from game.game.actions import Option
# from game.game.core import Hex, EffortFacet, Unit
#
#
# @dataclasses.dataclass
# class MoveOption(Option):
#     to_: Hex
#
#
# class Target(ABC): ...
#
#
# @dataclasses.dataclass
# class UnitTarget(Target):
#     unit: Unit
#
#
# T = TypeVar("T", bound=UnitTarget)
#
#
# @dataclasses.dataclass
# class EffortOption(Option, Generic[T]):
#     facet: EffortFacet
#     target: T
