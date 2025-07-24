from enum import StrEnum, auto


class GameStatus(StrEnum):
    PENDING = auto()
    PLAYING = auto()
    FINISHED = auto()
    EXPIRED = auto()
    CRASHED = auto()


class GameType(StrEnum):
    TUTORIAL = auto()
    SIMPLE = auto()
    ADVANCED = auto()
