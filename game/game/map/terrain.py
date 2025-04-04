from game.game.core import Terrain


class Ground(Terrain): ...


class Water(Terrain):

    def is_water(self) -> bool:
        return True
