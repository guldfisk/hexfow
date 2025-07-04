import { RefObject, useEffect, useRef } from "react";
import { useAppSelector } from "../state/hooks.ts";
import {
  GameState,
  Hex,
  LogLine,
  LogLineComponent,
  OptionBase,
  Unit,
} from "../interfaces/gameState.ts";
import {
  CostAtom,
  EffortCostSet,
  FacetDetails,
  GameObjectDetails,
  StatusDetails,
  UnitDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../images.ts";
import { MenuData } from "../actions/interface.ts";
import { menuDescribers } from "../actions/menues.ts";
import { ccToKey } from "../geometry.ts";
import { range } from "../utils/range.ts";

// const LogList = ({ logLines }: { logLines: string[] }) => {
//   const myRef: RefObject<HTMLDivElement | null> = useRef(null);
//   useEffect(() => {
//     if (myRef.current) {
//       myRef.current.scrollTop = myRef.current.scrollHeight;
//     }
//   });
//   return (
//     <div className="info-window event-log" id="event-log" ref={myRef}>
//       {logLines.map((log, idx) => (
//         <p key={idx}>{log}</p>
//       ))}
//     </div>
//   );
// };

const LogLineComponentView = ({ element }: { element: LogLineComponent }) => {
  if (element.type == "string") {
    return <div className={"log-component"}>{element.message + ""}</div>;
  }
  if (element.type == "unit") {
    return (
      <div className={"log-component highlighted-log-component"}>
        {element.blueprint + ""}
      </div>
    );
  }
  if (element.type == "hex") {
    return (
      <div className={"log-component highlighted-log-component"}>
        {ccToKey(element.cc) + ""}
      </div>
    );
  }
};

const LogLineView = ({ line: [indent, content] }: { line: LogLine }) => {
  return (
    <p>
      {"  ".repeat(indent)}
      {content.map((element) => (
        <LogLineComponentView element={element} />
      ))}
    </p>
  );
};

const LogList = ({ logLines }: { logLines: LogLine[] }) => {
  const myRef: RefObject<HTMLDivElement | null> = useRef(null);
  useEffect(() => {
    if (myRef.current) {
      myRef.current.scrollTop = myRef.current.scrollHeight;
    }
  });
  return (
    <div className="info-window event-log" id="event-log" ref={myRef}>
      {logLines.map((log, idx) => (
        <LogLineView line={log} key={idx} />
        // <p key={idx}>{log}</p>
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

const StatusDetailView = ({ status }: { status: StatusDetails }) => (
  <div className={"status-details"}>
    <div className={"facet-header"}>
      <img
        src={getImageUrl("status", status.identifier)}
        className={
          status.category == "unit" ? "status-icon-unit" : "status-icon-hex"
        }
      />
      {status.name}
    </div>
    {status.description ? (
      <div className={"facet-description"}>{status.description}</div>
    ) : null}
  </div>
);

const traverseStatuses = (
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

const UnitDetailsView = ({
  unit,
  details,
  //   TODO handle this in a non trash way
  gameObjectDetails,
}: {
  unit: Unit;
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
        <FacetDetailView facet={gameObjectDetails.facets[facet]} />
      ))}
      {relatedStatuses.map((statusIdentifier) => (
        <StatusDetailView
          status={gameObjectDetails.statuses[statusIdentifier]}
        />
      ))}
    </div>
  );
};

const HexDetailView = ({
  hex,
  //   TODO handle this in a non trash way
  gameObjectDetails,
}: {
  hex: Hex;
  gameObjectDetails: GameObjectDetails;
}) => {
  const terrainDetails = gameObjectDetails.terrain[hex.terrain];
  const relatedStatuses: string[] = [];
  for (const status of terrainDetails.related_statuses) {
    if (!relatedStatuses.includes(status)) {
      relatedStatuses.push(status);
      traverseStatuses(status, gameObjectDetails, relatedStatuses);
    }
  }
  return (
    <div>
      <div
        style={{
          fontSize: "18px",
        }}
      >
        {terrainDetails.name}
      </div>
      <img
        src={getImageUrl("terrain", hex.terrain)}
        className={"terrain-image"}
      />
      {terrainDetails.is_water ||
      terrainDetails.blocks_vision ||
      terrainDetails.is_high_ground ? (
        <div className={"facet-details"}>
          {terrainDetails.blocks_vision ? <div>Blocks vision</div> : null}
          {terrainDetails.is_water ? <div>Water</div> : null}
          {terrainDetails.is_high_ground ? <div>High ground</div> : null}
        </div>
      ) : null}
      {terrainDetails.description ? (
        <div className={"facet-details"}>{terrainDetails.description}</div>
      ) : null}

      {relatedStatuses.map((statusIdentifier) => (
        <StatusDetailView
          status={gameObjectDetails.statuses[statusIdentifier]}
        />
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
      <div>
        {menu
          ? menuDescribers[menu.type](gameState, menu)
          : gameState.decision.explanation}
      </div>
      {button}
      {/*{gameState.decision*/}
      {JSON.stringify(gameState.decision, null, 4)}
    </div>
  );
};

export const HUD = ({ connection }: { connection: WebSocket }) => {
  // TODO fucking LMAO
  const applicationState = useAppSelector((state) => state);

  let detailView = null;
  if (applicationState.gameObjectDetails && applicationState.detailed) {
    if (applicationState.detailed.type == "unit") {
      detailView = (
        <UnitDetailsView
          unit={applicationState.detailed.unit}
          details={
            applicationState.gameObjectDetails.units[
              applicationState.detailed.unit.blueprint
            ]
          }
          gameObjectDetails={applicationState.gameObjectDetails}
        />
      );
    } else if (applicationState.detailed.type == "hex") {
      detailView = (
        <HexDetailView
          hex={applicationState.detailed.hex}
          gameObjectDetails={applicationState.gameObjectDetails}
        />
      );
    }
  }

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {applicationState.gameState ? (
          <LogList logLines={applicationState.gameState.logs} />
        ) : null}

        <DecisionDetailView
          gameState={applicationState.gameState}
          connection={connection}
          menu={applicationState.menuData}
        />
      </div>

      <div className={"sidebar sidebar-right"}>
        <div className={"details-view"}>{detailView}</div>
      </div>
    </div>
  );
};
