import { RefObject, useEffect, useRef } from "react";
import { useAppSelector } from "../state/hooks.ts";
import { GameState, OptionBase, Unit } from "../interfaces/gameState.ts";
import {
  CostAtom,
  EffortCostSet,
  FacetDetails,
  UnitDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../images.ts";
import { MenuData } from "../actions/interface.ts";
import {menuDescribers} from "../actions/menues.ts";

const LogList = ({ logLines }: { logLines: string[] }) => {
  const myRef: RefObject<HTMLDivElement | null> = useRef(null);
  useEffect(() => {
    if (myRef.current) {
      myRef.current.scrollTop = myRef.current.scrollHeight;
    }
  });
  return (
    <div className="info-window event-log" id="event-log" ref={myRef}>
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
  const stats: string[] = [];

  if ("combineable" in facet && facet.combineable) {
    stats.push("combineable");
  }
  if ("max_activations" in facet && facet.max_activations != 1) {
    stats.push(
      facet.max_activations === null
        ? "unlimited activations"
        : `x${facet.max_activations} max activations`,
    );
  }
  if ("cost" in facet && facet.cost.atoms.length) {
    stats.push(`cost: ${effortCostToShort(facet.cost)}`);
  }
  if ("damage" in facet) {
    stats.push(`damage: ${facet.damage}`);
  }
  if ("range" in facet) {
    stats.push(`range: ${facet.range}`);
  }
  return stats.join(" ");
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

const DecisionDetailView = ({
  gameState,
  connection,
  menu,
}: {
  gameState: GameState | null;
  connection: WebSocket;
  menu: MenuData | null;
}) => {
  if (!gameState?.decision) {
    return (
      <div className="info-window decision-details" id="decision-description">
        "waiting for opponent"
      </div>
    );
  }

  let button = null;

  if (gameState.decision.type == "SelectOptionDecisionPoint") {
    const skipIndexes = gameState.decision.payload.options
      .map((option, idx) => [option, idx] as [OptionBase, number])
      .filter(([option]) => option.type == "SkipOption")
      .map(([_, idx]) => idx);

    if (skipIndexes.length) {
      button = (
        <button
          onClick={() => {
            connection.send(
              JSON.stringify({ index: skipIndexes[0], target: null }),
            );
          }}
        >
          Skip
        </button>
      );
    }
  }

  return (
    <div className="info-window decision-details" id="decision-description">
      <div>{menu ? menuDescribers[menu.type](gameState, menu) : gameState.decision.explanation}</div>
      {button}
      {/*{gameState.decision*/}
      {JSON.stringify(gameState.decision, null, 4) }
    </div>
  );
};

export const HUD = ({ connection }: { connection: WebSocket }) => {
  // TODO fucking LMAO
  const applicationState = useAppSelector((state) => state);

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {applicationState.gameState ? (
          <LogList logLines={applicationState.gameState.eventLog} />
        ) : null}

        <DecisionDetailView
          gameState={applicationState.gameState}
          connection={connection}
          menu={applicationState.menuData}
        />
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
