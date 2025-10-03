import "../../common.css";

import { Application, Container, Graphics, Ticker } from "pixi.js";

import { backgroundLoadTextures, loadGameTextures } from "./textures.ts";
import { renderMap } from "./rendering.ts";
import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { HUD } from "./hud/hud.tsx";
import { Provider } from "react-redux";
import {
  deactivateMenu,
  incrementAdditionalDetailsIndex,
  receiveGameState,
  renderedGameState,
  setActionFilter,
  store,
  toggleShowCoordinates,
} from "./state/store.ts";
import { Message } from "../interfaces/messages.ts";
import { TakeAction } from "./actions/interface.ts";
import { getBaseActions } from "./actions/actionSpace.ts";
import { ccToKey } from "../geometry.ts";
import { MapAnimation } from "./animations/interface.ts";

const gameConnection = new WebSocket(
  `ws://${window.location.hostname}:8765/ws`,
);
gameConnection.onmessage = (event) => {
  const result: Message = JSON.parse(event.data);
  if (result.message_type == "game_state") {
    console.log(result);
    store.dispatch(receiveGameState(result));
  } else if (result.message_type == "error") {
    console.log("ERROR!", result);
  } else {
    console.log("unknown message", result);
  }
};
gameConnection.onopen = () =>
  gameConnection.send(
    JSON.stringify({
      seat_id: new URLSearchParams(window.location.search).get("seat"),
    }),
  );

const makeDecision: TakeAction = (payload) => {
  const state = store.getState();
  const message = state.delayedActivation
    ? {
        count: state.gameStateId,
        payload: {
          index: state.delayedActivation.optionIndex,
          target: {
            index: state.delayedActivation.targetIndex,
          },
        },
        premove: Object.keys(payload).length
          ? {
              for_options: state.delayedActivation.options,
              payload: payload,
            }
          : null,
      }
    : { count: state.gameStateId, payload };
  console.log("sending", message);
  gameConnection.send(JSON.stringify(message));
};

async function main() {
  const app = new Application();
  await app.init({ resizeTo: window, antialias: true });
  // TODO
  document.body.appendChild(app.canvas);

  const gameObjectDetails = await loadGameTextures();
  backgroundLoadTextures(gameObjectDetails);

  let isDragging = false;
  let worldTranslation = { x: 0, y: 0 };
  let worldScale = 1;

  app.stage.on("pointerdown", (event) => {
    if (event.button == 1 || event.button == 2) {
      isDragging = true;
    }
  });

  app.stage.on("pointerup", (event) => {
    isDragging = false;
  });
  app.stage.on("pointermove", (event) => {
    if (isDragging) {
      worldTranslation = {
        x: worldTranslation.x + event.movementX,
        y: worldTranslation.y + event.movementY,
      };
    }
  });
  app.stage.on("wheel", (event) => {
    const oldScale = worldScale;
    worldScale = worldScale * (1 + event.deltaY / -1000);
    const pointingAtBefore = {
      x: (event.x - worldTranslation.x) / oldScale,
      y: (event.y - worldTranslation.y) / oldScale,
    };
    const pointingAtNow = {
      x: (event.x - worldTranslation.x) / worldScale,
      y: (event.y - worldTranslation.y) / worldScale,
    };
    worldTranslation = {
      x:
        worldTranslation.x +
        (pointingAtNow.x - pointingAtBefore.x) * worldScale,
      y:
        worldTranslation.y +
        (pointingAtNow.y - pointingAtBefore.y) * worldScale,
    };
  });
  app.stage.eventMode = "static";
  app.stage.hitArea = app.screen;

  // TODO disable normal browser zoom?

  // TODO YIKES
  document.oncontextmenu = document.body.oncontextmenu = function () {
    return false;
  };

  // TODO lmao
  const keyHandler = (event: KeyboardEvent) => {
    const state = store.getState();
    if (
      state.gameState &&
      state.gameState.decision &&
      state.gameState.decision["type"] == "SelectOptionDecisionPoint" &&
      (state.gameState.decision.explanation == "activate unit" &&
      !state.delayedActivation
        ? event.code == "KeyW"
        : event.code == "KeyS")
    ) {
      {
        for (const [idx, option] of (state.delayedActivation
          ? state.delayedActivation.options
          : state.gameState.decision.payload.options
        ).entries()) {
          if (option.type == "SkipOption") {
            makeDecision({ index: idx, target: {} });
          }
        }
      }
    } else if (event.key == "c") {
      store.dispatch(toggleShowCoordinates());
    } else if (event.key == "a" && state.delayedActivation) {
      makeDecision({});
    } else if (event.key == "Escape") {
      store.dispatch(deactivateMenu());
    } else if (event.key == "d") {
      store.dispatch(incrementAdditionalDetailsIndex());
    } else if (
      (parseInt(event.key) || event.key == "m") &&
      state.gameObjectDetails &&
      state.gameState
    ) {
      if (
        !state.gameState.decision ||
        !(
          state.delayedActivation ||
          state.gameState.decision.explanation == "select action"
        )
      ) {
        return;
      }

      const unit =
        state.gameState.active_unit_context?.unit ||
        state.delayedActivation?.unit;
      if (!unit) {
        return;
      }

      if (event.key == "m") {
        store.dispatch(setActionFilter({ type: "move" }));
        return;
      }

      const idx = parseInt(event.key);

      const facets = state.gameObjectDetails.units[unit.blueprint].facets;

      if (
        idx > facets.length ||
        state.gameObjectDetails.facets[facets[idx - 1]].category ==
          "static_ability"
      ) {
        return;
      }

      const actions = getBaseActions(
        state.gameState,
        state.gameObjectDetails,
        makeDecision,
        state.gameState.decision,
        state.gameState.active_unit_context,
        state.delayedActivation,
        { type: "facet", idx },
      );

      const hex = state.gameState.map.hexes.find(
        (h) => h.unit && h.unit.id == unit.id,
      );

      if (
        hex &&
        actions[ccToKey(hex.cc)] &&
        actions[ccToKey(hex.cc)].length == 1 &&
        actions[ccToKey(hex.cc)][0].type == "menu"
      ) {
        actions[ccToKey(hex.cc)][0].do({ x: 0, y: 0 });
      } else {
        store.dispatch(setActionFilter({ type: "facet", idx }));
      }
    }
  };

  document.addEventListener("keydown", keyHandler);

  let map = new Container();
  let previousGraphics: Graphics[] = [];
  app.stage.addChild(map);
  let elapsed: number = 0;
  let animations: MapAnimation[] = [];

  app.ticker.add((ticker: Ticker) => {
    const state = store.getState();

    if (state.shouldRerender && state.gameState && state.gameObjectDetails) {
      app.stage.removeChild(map);
      const result = renderMap(app, state, state.gameState, makeDecision);
      map = result.map;
      elapsed = 0;
      animations = result.animations;
      app.stage.addChild(map);
      for (const g of previousGraphics) {
        g.destroy();
      }
      previousGraphics = result.graphics;
      store.dispatch(renderedGameState());
    } else {
      elapsed += ticker.deltaMS;
    }
    animations = animations.filter((animation) => animation.play(elapsed));
    map.position = worldTranslation;
    map.scale = worldScale;
  });
}

await main();

createRoot(document.getElementById("hud")!).render(
  <StrictMode>
    <Provider store={store}>
      <HUD makeDecision={makeDecision} />
    </Provider>
  </StrictMode>,
);
