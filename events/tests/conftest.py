import pytest

from events.eventsystem import EventSystem
from events.tests.game_objects.dummy import Dummy


@pytest.fixture(autouse=True)
def dummy() -> None:
    Dummy.reset()


@pytest.fixture
def es() -> EventSystem:
    return EventSystem()
