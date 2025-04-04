import pytest

from events.eventsystem import EventSystem, ES


@pytest.fixture(autouse=True)
def refresh_session() -> None:
    ES.bind(EventSystem())
