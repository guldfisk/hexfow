import { AppState } from "../game/state/store.ts";
import { HoveredDetails } from "../interfaces/details.ts";
import { UnitDetailsView } from "./unitDetails.tsx";
import { StatusesDetailView } from "./statusDetails.tsx";
import React from "react";
import { HexDetailView } from "./hexDetail.tsx";
import { DetailsIndicator } from "../details/components.tsx";
import { FacetDetailView } from "./facetDetails.tsx";

export const DetailView = ({
  applicationState,
  detail,
  main,
}: {
  applicationState: AppState;
  detail: HoveredDetails;
  main: boolean;
}) => {
  let detailView = null;

  if (
    applicationState.gameObjectDetails &&
    applicationState.gameState &&
    detail
  ) {
    if (detail.type == "unit" || detail.type == "blueprint") {
      detailView = (
        <UnitDetailsView
          unit={detail.type == "unit" ? detail.unit : null}
          details={
            applicationState.gameObjectDetails.units[
              detail.type == "unit" ? detail.unit.blueprint : detail.blueprint
            ]
          }
          gameObjectDetails={applicationState.gameObjectDetails}
        />
      );
    } else if (detail.type == "hex") {
      detailView = (
        <HexDetailView
          hex={detail.hex}
          gameObjectDetails={applicationState.gameObjectDetails}
          gameState={applicationState.gameState}
        />
      );
    } else if (detail.type == "statuses") {
      detailView = (
        <StatusesDetailView
          statuses={detail.statuses}
          statusIdentifiers={null}
          gameObjectDetails={applicationState.gameObjectDetails}
        />
      );
    } else if (detail.type == "statusTypes") {
      detailView = (
        <StatusesDetailView
          statuses={null}
          statusIdentifiers={detail.statuses}
          gameObjectDetails={applicationState.gameObjectDetails}
        />
      );
    } else if (detail.type == "facet") {
      detailView = <FacetDetailView facet={detail.facet} unit={null} />;
    }
  }
  return (
    <div className={"details-view"}>
      {detailView}
      {main && applicationState.gameObjectDetails ? (
        <DetailsIndicator
          gameObjectDetails={applicationState.gameObjectDetails}
          detail={detail}
          additionalDetailsIndex={applicationState.additionalDetailsIndex}
        />
      ) : null}
    </div>
  );
};
