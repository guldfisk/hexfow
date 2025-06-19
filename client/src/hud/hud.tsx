import { RefObject, useEffect, useRef } from "react";
import { useAppSelector } from "../state/hooks.ts";
import { Unit } from "../interfaces/gameState.ts";
import {
  CostAtom,
  EffortCostSet,
  FacetDetails,
  UnitDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../images.ts";

const LogList = ({ logLines }: { logLines: string[] }) => {
  const myRef: RefObject<HTMLDivElement | null> = useRef(null);
  useEffect(() => {
    if (myRef.current) {
      myRef.current.scrollTop = myRef.current.scrollHeight;
    }
  });
  return (
    <div className="info-window" id="event-log" ref={myRef}>
      {logLines.map((log, idx) => (
        <p key={idx}>{log}</p>
      ))}
    </div>
  );
};

const effortCostAtomToShort = (cost: CostAtom): string => {
  switch (cost.type) {
    case "EnergyCost": {
      return `${cost.amount}E`;
    }
    case "MovementCost": {
      return `${cost.amount}M`;
    }
    case "ExclusiveCost": {
      return `Ex`;
    }
  }
};
const effortCostToShort = (cost: EffortCostSet): string =>
  cost.atoms.length ? cost.atoms.map(effortCostAtomToShort).join(" ") : "-";

const getFacetStatLine = (facet: FacetDetails): string => {
  switch (facet.category) {
    case "melee_attack": {
      return `cost: ${effortCostToShort(facet.cost)} damage: ${facet.damage}`;
    }
    case "ranged_attack": {
      return `cost: ${effortCostToShort(facet.cost)} damage: ${facet.damage}`;
    }
    case "activated_ability": {
      return `cost: ${effortCostToShort(facet.cost)}`;
    }
    case "static_ability": {
      return "";
    }
  }
};

const FacetDetailView = ({ facet }: { facet: FacetDetails }) => (
  <div className={"facet-details"}>
    <div className={"facet-header"}>
      <img src={getImageUrl("icon", facet.category)} className={"facet-icon"} />
      {facet.name}
    </div>
    <div className={"facet-stats"}>{getFacetStatLine(facet)}</div>
    {facet.description ? (
      <div className={"facet-description"}>{facet.description}</div>
    ) : null}
  </div>
);

const UnitDetailsView = ({
  unit,
  details,
}: {
  unit: Unit;
  details: UnitDetails;
}) => {
  return (
    <div>
      <img src={details.small_image} />

      <div
        style={{
          display: "inline-block",
          paddingLeft: "5px",
          verticalAlign: "top",
        }}
      >
        <div>{details.name}</div>
        <div>
          health: {unit.maxHealth - unit.damage}/{unit.maxHealth}
        </div>
        <div>speed: {unit.speed}</div>
        <div>sight: {unit.sight}</div>
        {unit.armor != 0 ? <div>armor: {unit.armor}</div> : null}
        {unit.energy != 0 || unit.maxEnergy != 0 ? (
          <div>
            energy: {unit.energy}/{unit.maxEnergy}
          </div>
        ) : null}
        <div>size: {unit.size}</div>
        <div>price: {details.price}</div>
      </div>

      {details.facets.map((facet) => (
        <FacetDetailView facet={facet} />
      ))}
    </div>
  );
};

export const HUD = () => {
  // TODO fucking LMAO
  const applicationState = useAppSelector((state) => state);

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {applicationState.gameState ? (
          <LogList logLines={applicationState.gameState.eventLog} />
        ) : null}

        <div className="info-window" id="decision-description">
          {JSON.stringify(applicationState?.gameState?.decision, null, 4)}
        </div>
      </div>

      <div className={"sidebar sidebar-right"}>
        {applicationState.hoveredUnit && applicationState.gameObjectDetails ? (
          <div className={"details-view"}>
            <UnitDetailsView
              unit={applicationState.hoveredUnit}
              details={
                applicationState.gameObjectDetails.units[
                  applicationState.hoveredUnit.blueprint
                ]
              }
            />
          </div>
        ) : (
          "idk"
        )}
      </div>
    </div>
  );
};
