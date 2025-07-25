import "./style.css";

import { Application, Container } from "pixi.js";
import { renderMap } from "./rendering.ts";
import {
  renderedGameState,
  setMapData,
  store,
  toggleIsObjective,
  updateTerrain,
  updateUnit,
} from "./state/store.ts";
import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { Provider } from "react-redux";
import { HUD } from "./hud.tsx";
import { loadGameTextures } from "./textures.ts";
import * as baseData from "./base.json";

const terrainMapping: { [key: string]: string } = {
  f: "forest",
  p: "plains",
  w: "water",
  m: "magma",
  h: "hills",
};

async function main() {
  const app = new Application();
  await app.init({ resizeTo: window, antialias: true });
  document.body.appendChild(app.canvas);

  await loadGameTextures();

  const keyHandler = (event: KeyboardEvent) => {
    const state = store.getState();
    if (state.hoveredHex) {
      if (Object.keys(terrainMapping).includes(event.key)) {
        store.dispatch(
          updateTerrain({
            cc: state.hoveredHex.cc,
            terrainType: terrainMapping[event.key],
          }),
        );
      } else if (event.key == "1" && state.selectedUnitIdentifier) {
        store.dispatch(
          updateUnit({
            cc: state.hoveredHex.cc,
            unitIdentifier: state.selectedUnitIdentifier,
          }),
        );
      } else if (event.key == "2") {
        store.dispatch(
          updateUnit({ cc: state.hoveredHex.cc, unitIdentifier: null }),
        );
      } else if (event.key == "3") {
        store.dispatch(toggleIsObjective(state.hoveredHex.cc));
      } else if (event.key == "e") {
        console.log(state.mapData);
      }
    }
  };

  document.addEventListener("keydown", keyHandler);

  store.dispatch(setMapData(Object.values(baseData.default)));

  let map = new Container();
  app.stage.addChild(map);

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

  app.ticker.add(() => {
    const state = store.getState();

    if (state.shouldRerender) {
      app.stage.removeChild(map);
      map = renderMap(app, state);
      app.stage.addChild(map);
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
      <HUD />
    </Provider>
  </StrictMode>,
);
