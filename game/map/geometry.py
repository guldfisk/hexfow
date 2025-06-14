from game.map.coordinates import CC


def hex_circle(radius: int = 1, center: CC = CC(0,0)) -> list[CC]:
    return [
        CC(r, h) + center
        for r in range(-radius, radius + 1)
        for h in range(-radius, radius + 1)
        if -radius <= -(r + h) <= radius
    ]
