import React from "react";
import { Status, UnitStatus } from "../interfaces/gameState.ts";
import {
  GameObjectDetails,
  StatusDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../image/images.ts";

const getStatusStatLine = (status: Status | UnitStatus): string => {
  const stats: string[] = [];

  if ("intention" in status) {
    stats.push(status.intention);
  }

  if (status.stacks) {
    stats.push(`stacks: ${status.stacks}`);
  }

  if (status.duration) {
    stats.push(`duration: ${status.duration} rounds`);
  }

  return stats.join(" - ");
};

export const StatusDetailView = ({
  status,
  statusDetails,
}: {
  status: Status | null;
  statusDetails: StatusDetails;
}) => (
  <div className={"status-details"}>
    <div className={"facet-header"}>
      <img
        src={getImageUrl("status", statusDetails.identifier)}
        className={
          statusDetails.category == "unit"
            ? "status-icon-unit"
            : "status-icon-hex"
        }
      />
      {statusDetails.name}
    </div>
    <div className={"status-stats"}>{statusDetails.stacking_info}</div>
    {!statusDetails.dispellable ? (
      <div className={"status-stats"}>undispellable</div>
    ) : null}
    {status ? (
      <div className={"status-stats"}>{getStatusStatLine(status)}</div>
    ) : null}
    {statusDetails.description ? (
      <div className={"facet-description"}>{statusDetails.description}</div>
    ) : null}
  </div>
);

export const StatusesDetailView = ({
  statuses,
  statusIdentifiers,
  //   TODO handle this in a non trash way
  gameObjectDetails,
}: {
  statuses: Status[] | UnitStatus[] | null;
  statusIdentifiers: string[] | null;
  gameObjectDetails: GameObjectDetails;
}) => {
  return (
    <>
      {statuses
        ? statuses.map((status) => (
            <StatusDetailView
              status={status}
              statusDetails={gameObjectDetails.statuses[status.type]}
            />
          ))
        : statusIdentifiers
          ? statusIdentifiers.map((identifier) => (
              <StatusDetailView
                status={null}
                statusDetails={gameObjectDetails.statuses[identifier]}
              />
            ))
          : null}
    </>
  );
};
