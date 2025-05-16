import dataclasses
from typing import Any

import pytest

from events.eventsystem import EventSystem, ES, Event


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
    # parser.addoption(
    #     "--only-changed",
    #     "--oc",
    #     action="store_true",
    #     help=(
    #         "Attempts to only collect tests that are changed, or imports changed files."
    #         " (Experimental, for local development convenience only)"
    #     ),
    # )

