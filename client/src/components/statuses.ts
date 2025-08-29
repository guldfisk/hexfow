import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";

export const traverseStatuses = (
  statusIdentifier: string,
  gameObjectDetails: GameObjectDetails,
  seen: string[],
) => {
  for (const related of gameObjectDetails.statuses[statusIdentifier]
    .related_statuses) {
    if (!seen.includes(related)) {
      seen.push(related);
      traverseStatuses(related, gameObjectDetails, seen);
    }
  }
};
