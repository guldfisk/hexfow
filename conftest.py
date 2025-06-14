from typing import Any


def pytest_addoption(parser: Any) -> None:
    parser.addoption(
        "--log-events",
        "--le",
        action="store_true",
        help="blah",
    )
    parser.addoption(
        "--log-game-states",
        "--lgs",
        action="store_true",
        help="blah",
    )
