import { RefObject, useEffect, useRef, useState } from "react";
import { useAppSelector } from "../state/hooks.ts";
import {
  GameState,
  Hex,
  LogLine,
  LogLineComponent,
  OptionBase,
  Status,
  Unit,
  UnitStatus,
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
import {
  highlightCCs,
  hoverDetail,
  removeCCHighlight,
  store,
} from "../state/store.ts";

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

const LogLineComponentView = ({
  element,
  unitMap,
}: {
  element: LogLineComponent;
  unitMap: { [key: string]: [Hex, Unit] };
}) => {
  const player = useAppSelector((state) => state.gameState?.player);
  const gameObjectDetails = useAppSelector((state) => state.gameObjectDetails);

  if (!player || !gameObjectDetails) {
    return;
  }

  if (element.type == "string") {
    return <div className={"log-component"}>{element.message + ""}</div>;
  }
  if (element.type == "unit") {
    return (
      //   TODO should highlight hex of unit / detail actual unit if the id is still known
      <div
        className={`log-component highlighted-log-component ${player == element.controller ? "allied" : "enemy"}-highlighted-log-component`}
        onMouseEnter={() => {
          if (unitMap[element.identifier]) {
            store.dispatch(
              hoverDetail({
                type: "unit",
                unit: unitMap[element.identifier][1],
              }),
            );
            store.dispatch(
              highlightCCs([ccToKey(unitMap[element.identifier][0].cc)]),
            );
          } else {
            console.log("HUH??+", element.blueprint, element);
            store.dispatch(
              hoverDetail({ type: "blueprint", blueprint: element.blueprint }),
            );
          }
        }}
        onMouseLeave={() => store.dispatch(removeCCHighlight())}
      >
        {gameObjectDetails.units[element.blueprint].name}
      </div>
    );
  }
  if (element.type == "hex") {
    return (
      <div
        className={"log-component highlighted-log-component"}
        onMouseEnter={() => store.dispatch(highlightCCs([ccToKey(element.cc)]))}
        onMouseLeave={() => store.dispatch(removeCCHighlight())}
      >
        {ccToKey(element.cc)}
      </div>
    );
  }
  if (element.type == "facet") {
    return (
      <div
        className={"log-component highlighted-log-component"}
        onMouseEnter={() => {
          const units = Object.values(gameObjectDetails.units).filter((unit) =>
            unit.facets.includes(element.identifier),
          );
          if (units.length == 1) {
            store.dispatch(
              hoverDetail({
                type: "blueprint",
                blueprint: units[0].identifier,
              }),
            );
          }
          //   TODO else idk
        }}
      >
        {gameObjectDetails.facets[element.identifier].name}
      </div>
    );
  }
  if (element.type == "status") {
    return (
      <div
        className={"log-component highlighted-log-component"}
        onMouseEnter={() => {
          store.dispatch(
            hoverDetail({
              type: "statusTypes",
              statuses: [element.identifier],
            }),
          );
        }}
      >
        {gameObjectDetails.statuses[element.identifier].name}
      </div>
    );
  }
  if (element.type == "list") {
    if (element.items.every((item) => item.type == "hex")) {
      return (
        <div
          className={"log-component highlighted-log-component"}
          onMouseEnter={() =>
            store.dispatch(
              highlightCCs(element.items.map((item) => ccToKey(item.cc))),
            )
          }
          onMouseLeave={() => store.dispatch(removeCCHighlight())}
        >
          {`${element.items.length} hexes`}
        </div>
      );
    }
    return element.items.map((item) => (
      <LogLineComponentView element={item} unitMap={unitMap} />
    ));
  }
};

const LogLineView = ({ line: [indent, content] }: { line: LogLine }) => {
  const map = useAppSelector((state) => state.gameState?.map);
  const unitMap = map
    ? Object.fromEntries(
        map.hexes
          .filter((h) => h.unit)
          .map((h: any) => [h.unit.id, [h, h.unit]]),
      )
    : {};

  return (
    <div className={"log-line"} style={{ paddingLeft: `${indent * 10}px` }}>
      {content.map((element) => (
        <LogLineComponentView element={element} unitMap={unitMap} />
      ))}
    </div>
  );
};

const LogList = ({ logLines }: { logLines: LogLine[] }) => {
  const [length, setLength] = useState(0);
  const myRef: RefObject<HTMLDivElement | null> = useRef(null);
  useEffect(() => {
    if (myRef.current) {
      if (logLines.length > length) {
        myRef.current.scrollTop = myRef.current.scrollHeight;
        setLength(logLines.length);
      }
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

const StatusDetailView = ({
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
    {status ? (
      <div className={"facet-stats"}>{getStatusStatLine(status)}</div>
    ) : null}
    {statusDetails.description ? (
      <div className={"facet-description"}>{statusDetails.description}</div>
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
          <div>
            health: {unit.maxHealth - unit.damage}/{unit.maxHealth}
          </div>
        ) : (
          <div>max health: {details.health}</div>
        )}
        <div>speed: {(unit || details).speed}</div>
        <div>sight: {(unit || details).sight}</div>
        {(unit || details).armor != 0 ? (
          <div>armor: {(unit || details).armor}</div>
        ) : null}
        {unit ? (
          unit.energy != 0 || unit.maxEnergy != 0 ? (
            <div>
              energy: {unit.energy}/{unit.maxEnergy}
            </div>
          ) : null
        ) : details.energy > 0 ? (
          <div>energy: {details.energy}</div>
        ) : null}
        <div>size: {(unit || details).size}</div>
        <div>price: {details.price}</div>
      </div>

      {details.facets.map((facet) => (
        <FacetDetailView facet={gameObjectDetails.facets[facet]} />
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
          status={null}
          statusDetails={gameObjectDetails.statuses[statusIdentifier]}
        />
      ))}
    </div>
  );
};

const StatusesDetailView = ({
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
    if (
      applicationState.detailed.type == "unit" ||
      applicationState.detailed.type == "blueprint"
    ) {
      detailView = (
        <UnitDetailsView
          unit={
            applicationState.detailed.type == "unit"
              ? applicationState.detailed.unit
              : null
          }
          details={
            applicationState.gameObjectDetails.units[
              applicationState.detailed.type == "unit"
                ? applicationState.detailed.unit.blueprint
                : applicationState.detailed.blueprint
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
    } else if (applicationState.detailed.type == "statuses") {
      detailView = (
        <StatusesDetailView
          statuses={applicationState.detailed.statuses}
          statusIdentifiers={null}
          gameObjectDetails={applicationState.gameObjectDetails}
        />
      );
    } else if (applicationState.detailed.type == "statusTypes") {
      detailView = (
        <StatusesDetailView
          statuses={null}
          statusIdentifiers={applicationState.detailed.statuses}
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
