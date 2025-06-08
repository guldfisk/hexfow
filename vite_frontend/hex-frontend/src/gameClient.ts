import "./style.css";

import {Application, Container,} from "pixi.js";
import {recursiveCamelCase} from "./utils/case.ts";

import {applicationState} from "./applicationState.ts";
import {loadGameTextures} from "./textures.ts";
import {renderMap} from "./rendering.ts";

async function main() {
  const app = new Application();
  await app.init({ resizeTo: window, antialias: false });
  document.body.appendChild(app.canvas);

  let map = new Container();

  app.stage.addChild(map);

  await loadGameTextures();

  const gameConnection = new WebSocket("ws://localhost:8765/ws");
  gameConnection.onmessage = (event) => {
    console.log(recursiveCamelCase(JSON.parse(event.data)));
    applicationState.gameState = recursiveCamelCase(JSON.parse(event.data));
    applicationState.shouldRerender = true;
  };

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

  // TODO YIKES
  document.oncontextmenu = document.body.oncontextmenu = function () {
    return false;
  };

  // TODO lmao
  const keyHandler = (event: KeyboardEvent) => {
    if (
      event.key == "s" &&
      applicationState.gameState &&
      applicationState.gameState.decision &&
      applicationState.gameState.decision["type"] == "SelectOptionDecisionPoint"
    ) {
      {
        for (const [idx, option] of applicationState.gameState.decision[
          "payload"
        ]["options"].entries()) {
          if (option["type"] == "SkipOption") {
            gameConnection.send(JSON.stringify({ index: idx, target: null }));
          }
        }
      }
    }
  };

  document.addEventListener("keydown", keyHandler);

  app.ticker.add(() => {
    if (
      applicationState.shouldRerender &&
      applicationState.gameState &&
      applicationState.gameObjectDetails
    ) {
      app.stage.removeChild(map);
      map = renderMap(
        app,
        applicationState.gameState,
        applicationState.gameObjectDetails,
        gameConnection,
      );
      app.stage.addChild(map);
      applicationState.shouldRerender = false;
    }
    map.position = worldTranslation;
    map.scale = worldScale;
  });
}

await main();
