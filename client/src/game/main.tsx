import "../../common.css";


import { Application, Container, Graphics } from "pixi.js";
import { recursiveCamelCase } from "./utils/case.ts";

import { loadGameTextures } from "./textures.ts";
import { renderMap } from "./rendering.ts";
import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { HUD } from "./hud/hud.tsx";
import { Provider } from "react-redux";
import {
  receiveGameState,
  renderedGameState,
  toggleShowCoordinates,
  store,
} from "./state/store.ts";

const gameConnection = new WebSocket(
  `ws://${window.location.hostname}:8765/ws`,
);
gameConnection.onmessage = (event) => {
  console.log(recursiveCamelCase(JSON.parse(event.data)));
  store.dispatch(receiveGameState(recursiveCamelCase(JSON.parse(event.data))));
};
gameConnection.onopen = () =>
  gameConnection.send(
    JSON.stringify({
      seat_id: new URLSearchParams(window.location.search).get("seat"),
    }),
  );

async function main() {
  const app = new Application();
  await app.init({ resizeTo: window, antialias: true });
  // TODO
  document.body.appendChild(app.canvas);

  let map = new Container();
  let previousGraphics: Graphics[] = [];
  app.stage.addChild(map);

  await loadGameTextures();

  let isDragging = false;
  let worldTranslation = { x: 0, y: 0 };
  let worldScale = 1;

  app.stage.on("pointerdown", (event) => {
    if (event.button == 1) {
      isDragging = true;
    }
  });

  app.stage.on("pointerup", (event) => {
    if (event.button == 1) {
      isDragging = false;
    }
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
  // document.oncontextmenu = document.body.oncontextmenu = function () {
  //   return false;
  // };

  // TODO lmao
  const keyHandler = (event: KeyboardEvent) => {
    const state = store.getState();
    if (
      state.gameState &&
      state.gameState.decision &&
      state.gameState.decision["type"] == "SelectOptionDecisionPoint" &&
      (state.gameState.decision.explanation == "activate unit?"
        ? event.code == "KeyW"
        : event.code == "KeyS")
    ) {
      {
        for (const [idx, option] of state.gameState.decision["payload"][
          "options"
        ].entries()) {
          if (option["type"] == "SkipOption") {
            gameConnection.send(JSON.stringify({ index: idx, target: null }));
          }
        }
      }
    } else if (event.key == "c") {
      store.dispatch(toggleShowCoordinates());
    }
  };

  document.addEventListener("keydown", keyHandler);

  app.ticker.add(() => {
    const state = store.getState();

    if (state.shouldRerender && state.gameState && state.gameObjectDetails) {
      app.stage.removeChild(map);
      const result = renderMap(app, state, state.gameState, gameConnection);
      map = result.map;
      app.stage.addChild(map);
      for (const g of previousGraphics) {
        g.destroy();
      }
      previousGraphics = result.graphics;
      store.dispatch(renderedGameState());
    }
    map.position = worldTranslation;
    map.scale = worldScale;
  });
}

await main();

createRoot(document.getElementById("hud")!).render(
  <StrictMode>
    <Provider store={store}>
      <HUD connection={gameConnection} />
    </Provider>
  </StrictMode>,
);
