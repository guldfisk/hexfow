import React from "react";
import { Unit } from "../interfaces/gameState.ts";
import {
  GameObjectDetails,
  UnitDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../image/images.ts";
import { ModifiedValue } from "./modifiedValue.tsx";
import { FacetDetailView } from "./facetDetails.tsx";
import { StatusDetailView } from "./statusDetails.tsx";
import { traverseStatuses } from "./statuses.ts";

const sizeNames = { "0": "Small", "1": "Medium", "2": "Large" };

export const UnitDetailsView = ({
  unit,
  details,
  //   TODO handle this in a non trash way
  gameObjectDetails,
}: {
  unit: Unit | null;
  details: UnitDetails;
  gameObjectDetails: GameObjectDetails;
}) => {
  const relatedStatuses: string[] = [];
  for (const facetName of details.facets) {
    for (const status of gameObjectDetails.facets[facetName].related_statuses) {
      if (!relatedStatuses.includes(status)) {
        relatedStatuses.push(status);
        traverseStatuses(status, gameObjectDetails, relatedStatuses);
      }
    }
  }
  return (
    <div>
      <img src={getImageUrl("unit", details.identifier)} />

      <div
        style={{
          display: "inline-block",
          paddingLeft: "5px",
          verticalAlign: "top",
        }}
      >
        <div>{details.name}</div>
        {unit ? (
          <>
            <div>
              health: {unit.max_health - unit.damage}/
              <ModifiedValue current={unit.max_health} base={details.health} />
            </div>
            <div>
              speed: <ModifiedValue current={unit.speed} base={details.speed} />
            </div>
            <div>
              sight: <ModifiedValue current={unit.sight} base={details.sight} />
            </div>
            {(unit || details).armor != 0 ? (
              <div>
                armor:{" "}
                <ModifiedValue current={unit.armor} base={details.armor} />
              </div>
            ) : null}
            {unit.energy != 0 || unit.max_energy != 0 ? (
              <div>
                energy: {unit.energy}/
                <ModifiedValue current={unit.max_energy} base={details.energy} />
              </div>
            ) : null}
          </>
        ) : (
          <>
            <div>max health: {details.health}</div>
            <div>speed: {details.speed}</div>
            <div>sight: {details.sight}</div>
            {details.armor != 0 ? <div>armor: {details.armor}</div> : null}
            {details.energy > 0 ? <div>energy: {details.energy}</div> : null}
          </>
        )}
        {/*TODO*/}
        <div>size: {sizeNames[(unit || details).size.toString()]}</div>
        <div>price: {details.price}</div>
      </div>
      {details.flavor ? (
        <div className={"facet-details"}>
          <i>{details.flavor}</i>
        </div>
      ) : null}
      {details.facets.map((facet) => (
        <FacetDetailView facet={gameObjectDetails.facets[facet]} unit={unit} />
      ))}
      {relatedStatuses.map((statusIdentifier) => (
        <StatusDetailView
          status={null}
          statusDetails={gameObjectDetails.statuses[statusIdentifier]}
        />
      ))}
    </div>
  );
};
