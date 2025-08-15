from events.eventsystem import ES
from game.core import HasStatuses, Unit
from game.events import DispelStatus
from game.values import StatusIntention


def dispel_all(target: HasStatuses) -> None:
    for status in list(target.statuses):
        ES.resolve(DispelStatus(target, status))


def dispel_from_unit(target: Unit, intention: StatusIntention | None = None) -> None:
    for status in list(target.statuses):
        if intention is None or status.intention == intention:
            ES.resolve(DispelStatus(target, status))
