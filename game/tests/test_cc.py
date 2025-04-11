from game.game.map.coordinates import CC


def test_distance():
    base = CC(0, 0)
    for cc in base.neighbors():
        for neighbor in cc.neighbors():
            assert cc.distance_to(neighbor) == 1
