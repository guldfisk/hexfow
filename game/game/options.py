# # import dataclasses
# # from abc import ABC
# # from typing import TypeVar, Generic
# #
# # from game.game.actions import Option
# # from game.game.core import Hex, EffortFacet, Unit
# #
# #
# # @dataclasses.dataclass
# # class MoveOption(Option):
# #     to_: Hex
# #
# #
# # class Target(ABC): ...
# #
# #
# # @dataclasses.dataclass
# # class UnitTarget(Target):
# #     unit: Unit
# #
# #
# # T = TypeVar("T", bound=UnitTarget)
# #
# #
# # @dataclasses.dataclass
# # class EffortOption(Option, Generic[T]):
# #     facet: EffortFacet
# #     target: T
#
#
# import dataclasses
# from typing import Any, Mapping
#
# from game.game.core import Unit
# from game.game.decisions import DecisionPoint, O, JSON, SerializationContext, Option
#
#
# @dataclasses.dataclass
# class SelectUnitOption(Option[Unit]):
#     options: list[Unit]
#     explanation: str
#
#     def get_explanation(self) -> str:
#         return self.explanation
#
#     def serialize_payload(self, context: SerializationContext) -> JSON:
#         return {
#             "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.options]
#         }
#
#     def parse_response(self, v: Mapping[str, Any]) -> Unit:
#         return self.options[v["index"]]
