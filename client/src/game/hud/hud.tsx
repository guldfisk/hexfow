import React, { RefObject, useEffect, useRef, useState } from "react";
import { useAppSelector } from "../state/hooks.ts";
import {
  GameState,
  Hex,
  LogLine,
  LogLineComponent,
  OptionBase,
  Unit,
} from "../../interfaces/gameState.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../../image/images.ts";
import { MenuData } from "../actions/interface.ts";
import { menuActionSpacers, menuDescribers } from "../actions/menues.ts";
import { ccToKey } from "../geometry.ts";
import {
  highlightCCs,
  hoverDetail,
  removeCCHighlight,
  store,
} from "../state/store.ts";
import { getBaseActionSpace } from "../actions/actionSpace.ts";
import { traverseStatuses } from "../../components/statuses.ts";
import {
  StatusDetailView,
  StatusesDetailView,
} from "../../components/statusDetails.tsx";
import { UnitDetailsView } from "../../components/unitDetails.tsx";

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
              highlightCCs([
                ccToKey(element.cc),
                ccToKey(unitMap[element.identifier][0].cc),
              ]),
            );
          } else {
            store.dispatch(
              hoverDetail({ type: "blueprint", blueprint: element.blueprint }),
            );
            store.dispatch(highlightCCs([ccToKey(element.cc)]));
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
  if (element.type == "player") {
    return (
      <div
        className={`log-component highlighted-log-component ${player == element.name ? "allied" : "enemy"}-highlighted-log-component`}
      >
        {element.name}
      </div>
    );
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

const HexDetailView = ({
  hex,
  //   TODO handle this in a non trash way
  gameObjectDetails,
  gameState,
}: {
  hex: Hex;
  gameObjectDetails: GameObjectDetails;
  gameState: GameState;
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
      <div className={"facet-details"}>
        {hex.visible
          ? "visible"
          : "not visible" +
            (hex.lastVisibleRound !== null &&
            gameState.round - hex.lastVisibleRound > 0
              ? ` - last visible ${gameState.round - hex.lastVisibleRound} rounds ago`
              : "")}
      </div>
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

const GameInfoView = ({ gameState }: { gameState: GameState }) => (
  <div>
    {gameState.players.map((player) => (
      <div>{`${player.name}${player.name == gameState.player ? " (you)" : ""}: ${player.points}/${gameState.targetPoints} points`}</div>
    ))}
    {`round: ${gameState.round}/10`}
  </div>
);

const DecisionDetailView = ({
  gameState,
  gameObjectDetails,
  connection,
  menu,
}: {
  gameState: GameState | null;
  gameObjectDetails: GameObjectDetails | null;
  connection: WebSocket;
  menu: MenuData | null;
}) => {
  if (!gameState?.decision || !gameObjectDetails) {
    return (
      <div className="info-window decision-details" id="decision-description">
        waiting for opponent
        {gameState ? <GameInfoView gameState={gameState} /> : null}
      </div>
    );
  }

  let button = null;

  // TODO common
  const actionSpace = menu
    ? menuActionSpacers[menu.type](
        gameState,
        gameObjectDetails,
        (body) => connection.send(JSON.stringify(body)),
        menu,
      )
    : getBaseActionSpace(
        gameState,
        (body) => connection.send(JSON.stringify(body)),
        gameObjectDetails,
        gameState.decision,
      );

  if (actionSpace.buttonAction) {
    button = (
      <button onClick={actionSpace.buttonAction.do}>
        {actionSpace.buttonAction.description}
      </button>
    );
  } else if (gameState.decision.type == "SelectOptionDecisionPoint") {
    const skipIndexes = gameState.decision.payload.options
      .map((option, idx) => [option, idx] as [OptionBase, number])
      .filter(([option]) => option.type == "SkipOption")
      .map(([_, idx]) => idx);

    if (skipIndexes.length) {
      button = (
        <button
          className={
            gameState.decision.explanation == "activate unit?"
              ? "alert-button"
              : ""
          }
          onClick={() => {
            connection.send(
              JSON.stringify({ index: skipIndexes[0], target: {} }),
            );
          }}
        >
          {gameState.decision.explanation == "activate unit?"
            ? "Wait"
            : "Skip rest of unit turn"}
        </button>
      );
    }
  }

  return (
    <div
      className="info-window decision-details"
      id="decision-description"
      style={{ borderColor: "#2f71e7" }}
    >
      <div>
        {menu
          ? menuDescribers[menu.type](gameState, gameObjectDetails, menu)
          : gameState.decision.explanation}
      </div>
      {button}
      {actionSpace.loadFileAction ? (
        <>
          <label>{actionSpace.loadFileAction.description}</label>
          <input
            type="file"
            id="fileInput"
            onChange={(event) => {
              let fr = new FileReader();

              fr.onload = () =>
                actionSpace.loadFileAction.do(fr.result as string);

              fr.readAsText(event.target.files[0]);
            }}
          />
        </>
      ) : null}
      {gameState ? <GameInfoView gameState={gameState} /> : null}
    </div>
  );
};

export const HUD = ({ connection }: { connection: WebSocket }) => {
  // TODO fucking LMAO
  const applicationState = useAppSelector((state) => state);

  let detailView = null;
  if (
    applicationState.gameObjectDetails &&
    applicationState.gameState &&
    applicationState.detailed
  ) {
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
          gameState={applicationState.gameState}
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
          gameObjectDetails={applicationState.gameObjectDetails}
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
