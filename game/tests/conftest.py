import dataclasses
from typing import Any, Callable

import pytest

from events.eventsystem import EventSystem, ES, Event


class TestScope:
    log_events: bool = False
    log_game_states: bool = False


class EventLogger:

    def __init__(self, callback: Callable[[str], ...] = print):
        self._stack_depth = 0
        self._callback = callback

    def __call__(self, event: Event, is_before: bool) -> None:
        if is_before:
            self._stack_depth += 1
            values = ", ".join(
                f"{field.name}: {getattr(event, field.name)}"
                for field in dataclasses.fields(event)
                if field.name not in ("parent", "children", "result")
            )

            stack_prepend = (
                "  │" * (self._stack_depth - 1) + "  ┌" if self._stack_depth > 0 else ""
            )
            self._callback(f"{stack_prepend} {type(event).__name__}({values})")
            # print(f"{stack_prepend} {type(event).__name__}({values})")
        else:
            self._stack_depth -= 1


@pytest.fixture(autouse=True, scope="session")
def setup_context(request: Any) -> None:
    TestScope.log_events = request.config.getoption("log_events")
    TestScope.log_game_states = request.config.getoption("log_game_states")


@pytest.fixture(autouse=True)
def event_session(setup_context: None) -> None:
    ES.bind(EventSystem())
    if TestScope.log_events:
        ES.register_event_callback(EventLogger())
