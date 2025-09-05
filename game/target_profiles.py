from __future__ import annotations

import dataclasses
import itertools
from typing import ClassVar

from pydantic import BaseModel

from game.core import GS, JSON, Hex, SerializationContext, TargetProfile, Unit
from game.map.coordinates import CC, Corner
from game.map.geometry import hex_arc, hex_ring
from game.schemas import (
    DecisionValidationError,
    IndexesSchema,
    IndexSchema,
    OrderedIndexesSchema,
    SingleCCSchema,
)


@dataclasses.dataclass
class NOfUnits(TargetProfile[list[Unit]]):
    response_schema: ClassVar[type[BaseModel]] = IndexesSchema

    units: list[Unit]
    select_count: int
    labels: list[str]
    min_count: int | None = None

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [
                {"id": context.player.id_map.get_id_for(unit)} for unit in self.units
            ],
            "select_count": self.select_count,
            "min_count": self.min_count,
            "labels": self.labels,
        }

    def parse_response_schema(self, v: IndexesSchema) -> list[Unit]:
        if self.min_count is not None:
            if len(v.indexes) < self.min_count:
                raise DecisionValidationError("not enough selected")
            if len(v.indexes) > self.select_count:
                raise DecisionValidationError("too many selected")
        elif len(v.indexes) != self.select_count:
            raise DecisionValidationError("invalid count selected")

        try:
            return [self.units[idx] for idx in v.indexes]
        except IndexError:
            raise DecisionValidationError("invalid index")


@dataclasses.dataclass
class NOfHexes(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = IndexesSchema

    hexes: list[Hex]
    select_count: int
    labels: list[str]
    min_count: int | None = None

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "hexes": [{"cc": hex_.position.serialize()} for hex_ in self.hexes],
            "select_count": self.select_count,
            "min_count": self.min_count,
            "labels": self.labels,
        }

    def parse_response_schema(self, v: IndexesSchema) -> list[Hex]:
        if self.min_count is not None:
            if len(v.indexes) < self.min_count:
                raise DecisionValidationError("not enough selected")
            if len(v.indexes) > self.select_count:
                raise DecisionValidationError("too many selected")
        elif len(v.indexes) != self.select_count:
            raise DecisionValidationError("invalid count selected")

        try:
            return [self.hexes[idx] for idx in v.indexes]
        except IndexError:
            raise DecisionValidationError("invalid index")


@dataclasses.dataclass
class ConsecutiveAdjacentHexes(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = SingleCCSchema

    adjacent_to: Hex
    arm_length: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "adjacent_to": self.adjacent_to.position.serialize(),
            "arm_length": self.arm_length,
        }

    def parse_response_schema(self, v: SingleCCSchema) -> list[Hex]:
        # TODO yikes
        cc = CC(v.cc.r, v.cc.h)
        if cc not in self.adjacent_to.position.neighbors():
            raise DecisionValidationError("invalid cc")
        return list(
            GS.map.get_hexes_of_positions(
                hex_arc(
                    radius=1,
                    arm_length=self.arm_length,
                    stroke_center=cc,
                    arc_center=self.adjacent_to.position,
                )
            )
        )


# TODO terrible name
@dataclasses.dataclass
class HexHexes(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    centers: list[Hex]
    radius: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "centers": [_hex.position.serialize() for _hex in self.centers],
            "radius": self.radius,
        }

    def parse_response_schema(self, v: IndexSchema) -> list[Hex]:
        try:
            center = self.centers[v.index]
        except IndexError:
            raise DecisionValidationError("invalid index")
        return list(GS.map.get_hexes_within_range_off(center, self.radius))


@dataclasses.dataclass
class TriHex(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    corners: list[Corner]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "corners": [corner.serialize() for corner in self.corners],
        }

    def parse_response_schema(self, v: IndexSchema) -> list[Hex]:
        try:
            corner = self.corners[v.index]
        except IndexError:
            raise DecisionValidationError("invalid index")
        return list(GS.map.get_hexes_of_positions(corner.get_adjacent_positions()))


@dataclasses.dataclass
class HexRing(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    centers: list[Hex]
    radius: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "centers": [_hex.position.serialize() for _hex in self.centers],
            "radius": self.radius,
        }

    def parse_response_schema(self, v: IndexSchema) -> list[Hex]:
        try:
            center = self.centers[v.index]
        except IndexError:
            raise DecisionValidationError("invalid index")
        return list(
            GS.map.get_hexes_of_positions(hex_ring(self.radius, center.position))
        )


@dataclasses.dataclass
class RadiatingLine(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    from_hex: Hex
    to_hexes: list[Hex]
    length: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "from_hex": self.from_hex.position.serialize(),
            "to_hexes": [h.position.serialize() for h in self.to_hexes],
            "length": self.length,
        }

    def parse_response_schema(self, v: IndexSchema) -> list[Hex]:
        try:
            selected_cc = self.to_hexes[v.index].position
        except IndexSchema:
            raise DecisionValidationError("invalid index")
        difference = selected_cc - self.from_hex.position
        return [
            projected
            for i in range(self.length)
            if (projected := GS.map.hexes.get(selected_cc + difference * i))
        ]


@dataclasses.dataclass
class Cone(TargetProfile[list[Hex]]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    from_hex: Hex
    to_hexes: list[Hex]
    arm_lengths: list[int]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "from_hex": self.from_hex.position.serialize(),
            "to_hexes": [h.position.serialize() for h in self.to_hexes],
            "arm_lengths": self.arm_lengths,
        }

    def parse_response_schema(self, v: IndexSchema) -> list[Hex]:
        try:
            selected_cc = self.to_hexes[v.index].position
        except IndexSchema:
            raise DecisionValidationError("invalid index")
        difference = selected_cc - self.from_hex.position
        return list(
            GS.map.get_hexes_of_positions(
                itertools.chain(
                    *(
                        hex_arc(
                            idx + 1,
                            arm_length=arm_length,
                            stroke_center=selected_cc + difference * idx,
                            arc_center=self.from_hex.position,
                        )
                        for idx, arm_length in enumerate(self.arm_lengths)
                    )
                )
            )
        )


@dataclasses.dataclass
class TreeNode:
    options: list[tuple[Unit | Hex, TreeNode | None]]
    label: str

    @classmethod
    def serialize_option(
        cls, option: Unit | Hex, context: SerializationContext
    ) -> JSON:
        if isinstance(option, Unit):
            return {"type": "unit", "id": context.player.id_map.get_id_for(option)}
        return {"type": "hex", "cc": option.position.serialize()}

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "label": self.label,
            "options": [
                (
                    self.serialize_option(game_object, context),
                    sub_tree.serialize(context) if sub_tree else None,
                )
                for game_object, sub_tree in self.options
            ],
        }


@dataclasses.dataclass
class Tree(TargetProfile[list[Unit | Hex]]):
    response_schema: ClassVar[type[BaseModel]] = OrderedIndexesSchema

    root_node: TreeNode

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"root_node": self.root_node.serialize(context)}

    def parse_response_schema(self, v: OrderedIndexesSchema) -> list[Unit | Hex]:
        selected = []
        current = self.root_node
        for idx in v.indexes:
            try:
                obj, node = current.options[idx]
            except IndexError:
                raise DecisionValidationError("invalid index")
            selected.append(obj)
            current = node
        if current:
            raise DecisionValidationError("not enough indexes")
        return selected
