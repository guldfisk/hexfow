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
import {
  ActionSpace,
  DelayedActivation,
  MenuData,
} from "../actions/interface.ts";
import { menuActionSpacers, menuDescribers } from "../actions/menues.ts";
import { ccToKey } from "../../geometry.ts";
import {
  highlightCCs,
  hoverDetail,
  removeCCHighlight,
  store,
} from "../state/store.ts";
import { getBaseActionSpace } from "../actions/actionSpace.ts";
import { getAdditionalDetails } from "../../details/additional.ts";
import { DetailView } from "../../components/details.tsx";
import { sortBlueprints, UnitList } from "../../components/unitList.tsx";

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
  if (element.type == "blueprint") {
    return (
      <div
        className={"log-component highlighted-log-component"}
        onMouseEnter={() => {
          store.dispatch(
            hoverDetail({ type: "blueprint", blueprint: element.blueprint }),
          );
        }}
      >
        {gameObjectDetails.units[element.blueprint].name}
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
    <div className="info-window" id="event-log" ref={myRef}>
      {logLines.map((log, idx) => (
        <LogLineView line={log} key={idx} />
      ))}
    </div>
  );
};

const GameInfoView = ({ gameState }: { gameState: GameState }) => (
  <div>
    {gameState.players.map((player) => (
      <div>{`${player.name}${player.name == gameState.player ? " (you)" : ""}: ${player.points}/${gameState.target_points} points`}</div>
    ))}
    {`round: ${gameState.round}/10`}
  </div>
);

const DecisionDetailView = ({
  gameState,
  gameObjectDetails,
  makeDecision,
  menu,
  delayedActivation,
  actionSpace,
}: {
  // TODO these not nullable
  gameState: GameState | null;
  gameObjectDetails: GameObjectDetails | null;
  makeDecision: (payload: { [key: string]: any }) => void;
  menu: MenuData | null;
  delayedActivation: DelayedActivation | null;
  actionSpace: ActionSpace;
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

  if (delayedActivation) {
    button = <button onClick={() => makeDecision({})}>Activate unit</button>;
  } else {
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
              makeDecision({ index: skipIndexes[0], target: {} });
            }}
          >
            {gameState.decision.explanation == "activate unit?"
              ? "Wait"
              : "Skip rest of unit turn"}
          </button>
        );
      }
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

export const HUD = ({
  makeDecision,
}: {
  makeDecision: (payload: { [key: string]: any }) => void;
}) => {
  // TODO fucking LMAO
  const applicationState = useAppSelector((state) => state);

  const gameState = applicationState.gameState;
  const gameObjectDetails = applicationState.gameObjectDetails;

  if (!gameState || !gameObjectDetails) {
    return <div className={"sidebar sidebar-left"}></div>;
  }

  const menu = applicationState.menuData;
  // TODO common
  const actionSpace = menu
    ? menuActionSpacers[menu.type](
        gameState,
        gameObjectDetails,
        makeDecision,
        menu,
      )
    : getBaseActionSpace(
        gameState,
        makeDecision,
        gameObjectDetails,
        gameState.decision,
        null,
        applicationState.delayedActivation,
      );

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {actionSpace.unitListActions ? (
          <>
            <div style={{ height: "20%" }}>
              <LogList logLines={gameState.logs} />
            </div>
            <div style={{ height: "45%" }}>
              <UnitList
                units={[...actionSpace.unitListActions.units].sort(
                  sortBlueprints,
                )}
                onClick={actionSpace.unitListActions.onClick}
                onHover={(unit) =>
                  store.dispatch(
                    hoverDetail({
                      type: "blueprint",
                      blueprint: unit.identifier,
                    }),
                  )
                }
              />
            </div>
          </>
        ) : (
          <div style={{ height: "70%" }}>
            <LogList logLines={gameState.logs} />
          </div>
        )}

        <DecisionDetailView
          gameState={applicationState.gameState}
          gameObjectDetails={applicationState.gameObjectDetails}
          makeDecision={makeDecision}
          menu={applicationState.menuData}
          delayedActivation={applicationState.delayedActivation}
          actionSpace={actionSpace}
        />
      </div>

      {applicationState.gameObjectDetails &&
      applicationState.detailed &&
      applicationState.additionalDetailsIndex !== null ? (
        <div className={"sidebar sidebar-details"}>
          <DetailView
            applicationState={applicationState}
            detail={
              getAdditionalDetails(
                applicationState.detailed,
                applicationState.gameObjectDetails,
              )[applicationState.additionalDetailsIndex]
            }
            main={false}
          />
        </div>
      ) : null}

      <div className={"sidebar sidebar-right"}>
        {applicationState.detailed ? (
          <DetailView
            applicationState={applicationState}
            detail={applicationState.detailed}
            main={true}
          />
        ) : null}
      </div>
    </div>
  );
};
