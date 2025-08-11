from __future__ import annotations

import itertools
import math
from enum import IntEnum
from typing import NamedTuple, Iterator, Mapping, Any, Iterable, Callable


class RC(NamedTuple):
    x: float
    y: float

    def __add__(self, other: RC) -> RC:
        return RC(self.x + other.x, self.y + other.y)

    def __sub__(self, other: RC) -> RC:
        return RC(self.x - other.x, self.y - other.y)

    def __mul__(self, other: float) -> RC:
        return RC(self.x * other, self.y * other)


class CC(NamedTuple):
    r: int
    h: int

    @property
    def l(self) -> int:
        return -sum(self)

    def __add__(self, other: CC) -> CC:
        return CC(self.r + other.r, self.h + other.h)

    def __sub__(self, other: CC) -> CC:
        return CC(self.r - other.r, self.h - other.h)

    def __mul__(self, other: int) -> CC:
        return CC(self.r * other, self.h * other)

    def neighbors(self) -> Iterator[CC]:
        for offset in NEIGHBOR_OFFSETS:
            yield self + offset

    def serialize(self) -> Mapping[str, Any]:
        return {"r": self.r, "h": self.h}

    def distance_to(self, to_: CC) -> int:
        difference = self - to_
        return (
            abs(difference.r) + abs(difference.r + difference.h) + abs(difference.h)
        ) // 2


class CornerPosition(IntEnum):
    TOP = 0
    BOTTOM = 1


class Corner(NamedTuple):
    cc: CC
    position: CornerPosition

    def get_adjacent_positions(self) -> list[CC]:
        return [
            self.cc,
            *(
                self.cc + offset
                for offset in (
                    NEIGHBOR_OFFSETS[:2]
                    if self.position == CornerPosition.BOTTOM
                    else NEIGHBOR_OFFSETS[3:5]
                )
            ),
        ]

    def serialize(self) -> Mapping[str, Any]:
        return {"cc": self.cc.serialize(), "position": self.position}


NEIGHBOR_OFFSETS = [
    CC(1, 0),
    CC(1, -1),
    CC(0, -1),
    CC(-1, 0),
    CC(-1, 1),
    CC(0, 1),
]


EDGE_COLLISION_DIRECTIONS: list[tuple[CC, tuple[CC, CC]]] = [
    (
        NEIGHBOR_OFFSETS[i] + NEIGHBOR_OFFSETS[(i + 1) % 6],
        (
            NEIGHBOR_OFFSETS[i],
            NEIGHBOR_OFFSETS[(i + 1) % 6],
        ),
    )
    for i in range(6)
]


# TODO
HEX_SIZE = 45

HEX_WIDTH = math.sqrt(3) * HEX_SIZE
HEX_HEIGHT = 2 * HEX_SIZE


VERTEX_OFFSETS = [
    RC(HEX_WIDTH / 2, -HEX_SIZE / 2),
    RC(0, -HEX_SIZE),
    RC(-HEX_WIDTH / 2, -HEX_SIZE / 2),
    RC(-HEX_WIDTH / 2, HEX_SIZE / 2),
    RC(0, HEX_HEIGHT / 2),
    RC(HEX_WIDTH / 2, HEX_SIZE / 2),
]


def cc_to_rc(cc: CC) -> RC:
    return RC(
        HEX_SIZE * ((math.sqrt(3) / 2) * cc.r + math.sqrt(3) * cc.h),
        HEX_SIZE * ((3 / 2) * cc.r),
    )


def is_left(line_from: RC, line_to: RC, point: RC) -> float:
    return (line_to.x - line_from.x) * (point.y - line_from.y) - (
        line_to.y - line_from.y
    ) * (point.x - line_from.x)


def cartesian_collides(line_from: RC, line_to: RC, shape: Iterable[RC]) -> bool:
    seen_left = False
    seen_right = False

    for point in shape:
        v = is_left(line_from, line_to, point)
        if v == 0:
            return True
        if v > 0:
            seen_left = True
        else:
            seen_right = True
        if seen_left and seen_right:
            return True
    return False


def get_check_directions_for_cartesian(from_point: RC, to_point: RC) -> list[CC]:
    if to_point.x > from_point.x:
        if to_point.y < from_point.y:
            return [CC(-1, 0), CC(-1, 1), CC(0, 1)]
        else:
            return [CC(0, 1), CC(1, 0), CC(1, -1)]
    else:
        if to_point.y < from_point.y:
            return [CC(0, -1), CC(-1, 0), CC(-1, 1)]
        else:
            return [CC(0, -1), CC(1, -1), CC(1, 0)]


def get_check_directions(from_cc: CC, to_cc: CC) -> list[CC]:
    return get_check_directions_for_cartesian(cc_to_rc(from_cc), cc_to_rc(to_cc))


def find_cartesian_collisions(line_from: CC, line_to: CC) -> list[CC]:
    collisions: list[CC] = []
    directions = get_check_directions(line_from, line_to)
    real_from = cc_to_rc(line_from)
    real_to = cc_to_rc(line_to)

    currently_checking = line_from
    checking_next = line_from

    while currently_checking != line_to:
        for direction in directions:
            position = currently_checking + direction
            checking_real_position = cc_to_rc(position)

            if cartesian_collides(
                real_from,
                real_to,
                [checking_real_position + offset * 1.01 for offset in VERTEX_OFFSETS],
            ):
                if position != line_to:
                    collisions.append(position)
                checking_next = position
        currently_checking = checking_next

    return collisions


def find_collisions(line_from: CC, line_to: CC) -> list[list[CC]]:
    relative_to = line_to - line_from
    for offset, backwards in EDGE_COLLISION_DIRECTIONS:
        if (
            (offset.r > 0) == (relative_to.r > 0)
            and (offset.h > 0) == (relative_to.h > 0)
            and (
                relative_to.h % offset.h == 0
                if offset.r == 0
                else (
                    relative_to.r % offset.r == 0
                    if offset.h == 0
                    else relative_to.r / offset.r == relative_to.h / offset.h
                    and relative_to.r % offset.r == 0
                )
            )
        ):
            return list(
                itertools.chain(
                    *(
                        [
                            [offset * i + line_from - b for b in backwards],
                            *(
                                ([offset * i + line_from],)
                                if offset * i + line_from != line_to
                                else ()
                            ),
                        ]
                        for i in range(
                            1,
                            (
                                relative_to.r // offset.r
                                if offset.r > 0
                                else relative_to.h // offset.h
                            )
                            + 1,
                        )
                    )
                )
            )
    return [[v] for v in find_cartesian_collisions(line_from, line_to)]


def line_of_sight_obstructed(
    line_from: CC, line_to: CC, obstruction_getter: Callable[[CC], bool]
) -> bool:
    collided_sides = [False, False]

    for coordinates in find_collisions(line_from, line_to):
        if len(coordinates) == 1:
            if obstruction_getter(coordinates[0]):
                return True
        else:
            for idx, c in enumerate(coordinates):
                if obstruction_getter(c):
                    collided_sides[idx] = True
            if all(collided_sides):
                return True

    return False
