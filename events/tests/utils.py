import dataclasses

from events.eventsystem import Event, EventSystem


def check_history(es: EventSystem, target: list[Event]):
    assert [
        type(e)(
            **{
                f.name: getattr(e, f.name)
                for f in dataclasses.fields(e)
                if f.name not in ("parent", "children")
            }
        )
        for e in es.history
    ] == target
