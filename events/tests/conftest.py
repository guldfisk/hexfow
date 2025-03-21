import pytest

from events.eventsystem import EventSystem, ES
from events.tests.game_objects.dummy import Dummy


@pytest.fixture(autouse=True)
def dummy() -> None:
    Dummy.reset()


@pytest.fixture(autouse=True)
def refresh_session() -> None:
    ES.bind(EventSystem())
