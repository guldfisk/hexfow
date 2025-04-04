from __future__ import annotations

from typing import NamedTuple, Iterator


class CubeCoordinate(NamedTuple):
    r: int
    h: int

    @property
    def l(self) -> int:
        return -sum(self)

    def __add__(self, other: CubeCoordinate) -> CubeCoordinate:
        return CubeCoordinate(self.r + other.r, self.h + other.h)

    def neighbors(self) -> Iterator[CubeCoordinate]:
        for offset in neighbor_offsets:
            yield self + offset


neighbor_offsets = [
    CubeCoordinate(1, 0),
    CubeCoordinate(1, -1),
    CubeCoordinate(0, -1),
    CubeCoordinate(-1, 0),
    CubeCoordinate(-1, 1),
    CubeCoordinate(0, 1),
]
