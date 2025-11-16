from abc import ABC, abstractmethod
from typing import ClassVar

from game.core import (
    GS,
    ActivatedAbilityFacet,
    Hex,
    NoneResult,
    NoTarget,
    ObjectListResult,
    OneOfHexes,
    OneOfUnits,
    SingleObjectResult,
    TargetProfile,
    Unit,
    find_hexs_within_range,
    find_units_within_range,
)
from game.target_profiles import (
    ConsecutiveAdjacentHexes,
    HexHexes,
    HexRing,
    RadiatingLine,
    Tree,
    TreeNode,
    TriHex,
)
from game.values import ControllerTargetOption


class NoTargetActivatedAbility(ActivatedAbilityFacet[NoneResult], ABC):
    def get_target_profile(self) -> TargetProfile[NoneResult] | None:
        return NoTarget()

    @abstractmethod
    def perform(self, target: None) -> None: ...


class TargetUnitActivatedAbility(ActivatedAbilityFacet[SingleObjectResult[Unit]], ABC):
    range: ClassVar[int] = 1
    requires_los: ClassVar[bool] = True
    can_target_self: ClassVar[bool] = True
    controller_target_option: ClassVar[ControllerTargetOption | None] = None

    explain_qualifier_filter: ClassVar[str | None] = None
    explain_with_filter: ClassVar[str | None] = None
    explain_that_filter: ClassVar[str | None] = None

    def filter_unit(self, unit: Unit) -> bool:
        return True

    @classmethod
    def get_target_explanation(cls) -> str:
        adjacent = cls.range == 1 and (
            cls.controller_target_option == ControllerTargetOption.ENEMY
            or not cls.can_target_self
        )
        fragments: list[str] = ["Target"]
        if adjacent:
            fragments.append("adjacent")
        if not cls.can_target_self and not adjacent:
            fragments.append("other")
        if cls.controller_target_option:
            fragments.append(cls.controller_target_option)
        if cls.explain_qualifier_filter:
            fragments.append(cls.explain_qualifier_filter)
        fragments.append("unit")
        if cls.explain_with_filter:
            fragments.append(cls.explain_with_filter)
        if not adjacent:
            fragments.append(f"within {cls.range} range")
            if cls.range > 1:
                fragments.append("LoS" if cls.requires_los else "NLoS")
        if cls.explain_that_filter:
            fragments.append(cls.explain_that_filter)
        return " ".join(fragments) + "."

    def get_target_profile(self) -> TargetProfile[SingleObjectResult[Unit]] | None:
        if units := find_units_within_range(
            self.parent,
            self.range,
            require_los=self.requires_los,
            with_controller=self.controller_target_option,
            can_include_self=self.can_target_self,
            additional_filter=self.filter_unit,
        ):
            return OneOfUnits(units)

    @abstractmethod
    def perform(self, target: SingleObjectResult[Unit]) -> None: ...


class TargetHexActivatedAbility(ActivatedAbilityFacet[SingleObjectResult[Hex]], ABC):
    range: ClassVar[int] = 1
    min_range: ClassVar[int | None] = None
    requires_los: ClassVar[bool] = True
    requires_vision: ClassVar[bool] = True
    requires_empty: ClassVar[bool] = False
    can_target_self: ClassVar[bool] = True

    explain_qualifier_filter: ClassVar[str | None] = None
    explain_with_filter: ClassVar[str | None] = None
    explain_that_filter: ClassVar[str | None] = None
    explain_hex_alias: ClassVar[str | None] = None

    def filter_hex(self, hex_: Hex) -> bool:
        return True

    @classmethod
    def get_target_explanation(cls) -> str:
        adjacent = cls.range == 1 and (not cls.can_target_self or cls.requires_empty)
        fragments: list[str] = ["Target"]
        if adjacent:
            fragments.append("adjacent")
        elif not cls.can_target_self:
            fragments.append("other")
        if cls.requires_vision:
            fragments.append("visible")
        if cls.requires_empty:
            fragments.append("empty")
        if cls.explain_qualifier_filter:
            fragments.append(cls.explain_qualifier_filter)
        fragments.append(cls.explain_hex_alias or "hex")
        if cls.explain_with_filter:
            fragments.append(cls.explain_with_filter)
        if not adjacent:
            fragments.append(f"within {cls.range} range")
            if cls.min_range is not None:
                fragments.append(f"and at least {cls.min_range} hexes away")
            if cls.range > 1:
                fragments.append("LoS" if cls.requires_los else "NLoS")
        if cls.explain_that_filter:
            fragments.append(cls.explain_that_filter)
        return " ".join(fragments) + "."

    def get_target_profile(self) -> TargetProfile[SingleObjectResult[Hex]] | None:
        if hexes := find_hexs_within_range(
            self.parent,
            self.range,
            min_distance=self.min_range,
            require_vision=self.requires_vision,
            require_los=self.requires_los,
            require_empty=self.requires_empty,
            can_include_self=self.can_target_self,
            additional_filter=lambda h: self.filter_hex(h),
        ):
            return OneOfHexes(hexes)

    @abstractmethod
    def perform(self, target: SingleObjectResult[Hex]) -> None: ...


class TargetHexArcActivatedAbility(ActivatedAbilityFacet[ObjectListResult[Hex]], ABC):
    arm_length: ClassVar[int] = 1

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return f"Target length {1 + cls.arm_length * 2} adjacent arc of hexes."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        return ConsecutiveAdjacentHexes(GS.map.hex_off(self.parent), self.arm_length)

    @abstractmethod
    def perform(self, target: ObjectListResult[Hex]) -> None: ...


class TargetRadiatingLineActivatedAbility(
    ActivatedAbilityFacet[ObjectListResult[Hex]], ABC
):
    length: ClassVar[int]

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return f"Target length {cls.length} radiating line of hexes."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        return RadiatingLine(
            GS.map.hex_off(self.parent),
            list(GS.map.get_neighbors_off(self.parent)),
            self.length,
        )

    @abstractmethod
    def perform(self, target: ObjectListResult[Hex]) -> None: ...


class TargetHexCircleActivatedAbility(
    ActivatedAbilityFacet[ObjectListResult[Hex]], ABC
):
    range: ClassVar[int]
    radius: ClassVar[int] = 1

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return f"Target radius {cls.radius} hex circle, center within {cls.range} NLoS."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        if hexes := [
            _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, self.range)
        ]:
            return HexHexes(hexes, self.radius)

    @abstractmethod
    def perform(self, target: ObjectListResult[Hex]) -> None: ...


class TargetHexRingActivatedAbility(ActivatedAbilityFacet[ObjectListResult[Hex]], ABC):
    range: ClassVar[int]
    radius: ClassVar[int] = 1

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return f"Target radius {cls.radius} hex ring, center within {cls.range} NLoS."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        if hexes := [
            _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, self.range)
        ]:
            return HexRing(hexes, self.radius)

    @abstractmethod
    def perform(self, target: ObjectListResult[Hex]) -> None: ...


class TargetTriHexActivatedAbility(ActivatedAbilityFacet[ObjectListResult[Hex]], ABC):
    range: ClassVar[int]
    min_range: ClassVar[int | None] = None

    @classmethod
    def get_target_explanation(cls) -> str | None:
        s = f"Target tri hex within {cls.range} range "
        if cls.min_range is not None:
            s += f"and at least {cls.min_range} hexes away "
        return s + "NLoS."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        if corners := list(
            GS.map.get_corners_within_range_off(
                self.parent, self.range, min_distance=self.min_range
            )
        ):
            return TriHex(corners)

    @abstractmethod
    def perform(self, target: ObjectListResult[Hex]) -> None: ...


class PincersActivatedAbility(ActivatedAbilityFacet[ObjectListResult[Hex]], ABC):
    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target two visible hexes adjacent to this unit, with one hex also adjacent to this unit between them."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        # TODO edge??
        if (
            len(
                hexes := [
                    h
                    for h in GS.map.get_neighbors_off(self.parent)
                    if h.is_visible_to(self.parent.controller)
                ]
            )
            >= 2
        ):
            return Tree(
                TreeNode(
                    [
                        (
                            _hex,
                            TreeNode(
                                [
                                    (hexes[(idx + offset) % len(hexes)], None)
                                    for offset in (-2, 2)
                                ],
                                "select second hex",
                            ),
                        )
                        for idx, _hex in enumerate(hexes)
                    ],
                    "select first hex",
                )
            )
