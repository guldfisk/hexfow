import { HoveredDetails } from "../interfaces/details.ts";
import { getAdditionalDetails } from "./additional.ts";
import React from "react";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";

export const DetailsIndicator = ({
  gameObjectDetails,
  detail,
  additionalDetailsIndex,
}: {
  gameObjectDetails: GameObjectDetails;
  detail: HoveredDetails;
  additionalDetailsIndex: number | null;
}) => {
  const options = getAdditionalDetails(detail, gameObjectDetails);
  if (!options.length) {
    return null;
  }

  return (
    <div className={"details-indicator"}>
      {`press d for details (${
        additionalDetailsIndex !== null ? `${additionalDetailsIndex + 1}/` : ""
      }${options.length})`}
    </div>
  );
};
