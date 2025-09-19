from typing import TypeAlias

from events.eventsystem import ES, EventResolution
from game.core import (
    HasStatuses,
    Hex,
    HexStatus,
    HexStatusSignature,
    Source,
    Unit,
    UnitStatus,
    UnitStatusSignature,
)
from game.events import ApplyHexStatus, ApplyStatus, DispelStatus
from game.values import StatusIntention


UnitStatusType: TypeAlias = UnitStatus | str
HexStatusType: TypeAlias = HexStatus | str


def dispel_all(target: HasStatuses) -> None:
    for status in list(target.statuses):
        ES.resolve(DispelStatus(target, status))


def dispel_from_unit(target: Unit, intention: StatusIntention | None = None) -> None:
    for status in list(target.statuses):
        if intention is None or status.intention == intention:
            ES.resolve(DispelStatus(target, status))


def apply_status_to_unit(
    unit: Unit,
    status: UnitStatusType,
    source: Source,
    *,
    duration: int | None = None,
    stacks: int | None = None,
    intention: StatusIntention | None = None,
) -> EventResolution:
    return ES.resolve(
        ApplyStatus(
            unit,
            UnitStatusSignature(
                status if isinstance(status, UnitStatus) else UnitStatus.get(status),
                source,
                stacks=stacks,
                duration=duration,
                intention=intention,
            ),
        )
    )


def apply_status_to_hex(
    hex_: Hex,
    status: HexStatusType,
    source: Source,
    *,
    duration: int | None = None,
    stacks: int | None = None,
) -> EventResolution:
    return ES.resolve(
        ApplyHexStatus(
            hex_,
            HexStatusSignature(
                status if isinstance(status, HexStatus) else HexStatus.get(status),
                source,
                stacks=stacks,
                duration=duration,
            ),
        )
    )
