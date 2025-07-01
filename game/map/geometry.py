import itertools

from game.map.coordinates import CC


def hex_circle(radius: int = 1, center: CC = CC(0, 0)) -> list[CC]:
    return [
        CC(r, h) + center
        for r in range(-radius, radius + 1)
        for h in range(-radius, radius + 1)
        if -radius <= -(r + h) <= radius
    ]


def hex_ring(radius: int, center: CC = CC(0, 0)) -> list[CC]:
    return [
        cc + center
        for cc in itertools.chain(
            (CC(-radius, i) for i in range(radius + 1)),
            (CC(i, radius) for i in range(-radius + 1, 1)),
            (CC(i + 1, radius - 1 - i) for i in range(radius - 1)),
            (CC(radius, i) for i in reversed(range(-radius, 1))),
            (CC(i, -radius) for i in reversed(range(radius))),
            (CC(-(i + 1), -(radius - 1 - i)) for i in range(radius - 1)),
        )
    ]


def hex_arc(
    radius: int, arm_length: int, stroke_center: CC, arc_center: CC = CC(0, 0)
) -> list[CC]:
    hexes = hex_ring(radius, center=arc_center)
    for idx, cc in enumerate(hexes):
        if cc == stroke_center:
            return [
                hexes[(idx + offset) % len(hexes)]
                for offset in range(-arm_length, arm_length + 1)
            ]
    raise ValueError("Invalid stroke center")
