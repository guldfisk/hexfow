import "./style.css";

import {
  Application,
  Assets,
  Container,
  Graphics,
  GraphicsContext,
  Sprite,
  Text,
  TextStyle,
  Texture,
} from "pixi.js";
import { CC, GameState, Hex, Size } from "./interfaces/gameState.ts";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";
import { ApplicationState } from "./interfaces/applicationState.ts";
import { recursiveCamelCase } from "./utils/case.ts";

import {GameObjectDetails} from "./interfaces/gameObjectDetails.ts";

const hexSize = 160;

interface RC {
  x: number;
  y: number;
}

const hexWidth = Math.sqrt(3) * hexSize;
const hexHeight = hexSize * 2;

const hexVerticeOffsets: [number, number][] = [
  [hexWidth / 2, -hexSize / 2],
  [0, -hexSize],
  [-hexWidth / 2, -hexSize / 2],
  [-hexWidth / 2, hexSize / 2],
  [0, hexHeight / 2],
  [hexWidth / 2, hexSize / 2],
];

const CCToRC = (hexCoord: CC): RC => ({
  x: hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  y: hexSize * ((3 / 2) * hexCoord.r),
});

const addRCs = (a: RC, b: RC): RC => ({
  x: a.x + b.x,
  y: a.y + b.y,
});

const hexDistance = (fromCC: CC, toCC: CC): number => {
  const r = fromCC.r - toCC.r;
  const h = fromCC.h - toCC.h;
  return (Math.abs(r) + Math.abs(r + h) + Math.abs(h)) / 2;
};

const sizeMap: { S: number; M: number; L: number } = { S: 0.8, M: 1, L: 1.2 };

const textureMap: { [key: string]: Texture } = {};

const renderMap = (
  app: Application,
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  gameConnection: WebSocket,
): Container => {
  // TODO this shouldn't be here
  let maxX = window.innerWidth;
  let maxY = window.innerHeight;
  let center = { x: maxX / 2, y: maxY / 2 };
  //
  // console.log("rendering", gameState);

  // document.body.appendChild(app.canvas);

  const eventLog = document.getElementById("event-log");

  if (eventLog) {
    eventLog.replaceChildren(
      ...gameState.eventLog.map((log) => {
        const element = document.createElement("p");
        element.textContent = log;
        return element;
      }),
    );
    eventLog.scrollTop = eventLog.scrollHeight;
  }

  document.getElementById("decision-description").textContent = JSON.stringify(
    gameState.decision,
    null,
    4,
  );

  // TODO not here
  const getHexShape = (color: FillInput): GraphicsContext => {
    let hexShape = new GraphicsContext()
      .setStrokeStyle({ color: "red", pixelLine: true })
      .moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath().fill(color);
    // hexShape.closePath();
    // hexShape.stroke();
    return hexShape;
  };
  const getHexFrame = (color: FillInput): GraphicsContext => {
    let hexShape = new GraphicsContext()
      .setStrokeStyle({ color, width: 3, alignment: 1 })
      // .setStrokeStyle({ color, pixelLine: true })
      .moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath();
    hexShape.stroke();
    return hexShape;
  };
  // const visibleHexShape = getHexShape("447744");
  // const invisibleHexShape = getHexShape("black");
  const visibleHexShape = getHexShape({ color: "447744", alpha: 0 });
  const invisibleHexShape = getHexShape({ color: "black", alpha: 100 });
  const fullHexShape = getHexShape("red");

  const selectableFrame = getHexFrame("blue");

  // TODO not here
  const smallTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 12,
    fill: 0xff1010,
    align: "center",
  });
  const healthTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 20,
    fill: 0xff1010,
    align: "center",
  });
  const largeTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 80,
    fill: "blue",
    align: "center",
    stroke: "white",
  });

  const map = new Container();

  app.stage.addChild(map);

  const unitHexes: { [key: string]: Hex } = Object.fromEntries(
    gameState.map.hexes.filter((h) => h.unit).map((h) => [h.unit.id, h]),
  );

  type Action = { [key: string]: any };
  const hexActionMap: { [key: string]: Action } = {};

  const ccToKey = (cc: CC): string => `${cc.r},${cc.h}`;

  if (
    gameState.decision &&
    gameState.decision["type"] == "SelectOptionDecisionPoint"
  ) {
    // console.log("ok");
    for (const [idx, option] of gameState.decision["payload"][
      "options"
    ].entries()) {
      // console.log(option["targetProfile"]);
      if (option["targetProfile"]["type"] == "OneOfUnits") {
        // console.log("units");

        for (const [targetIdx, unit] of option["targetProfile"]["values"][
          "units"
        ].entries()) {
          // console.log(unitHexes[unit["id"]].cc);
          // console.log(ccToKey(unitHexes[unit["id"]].cc));

          hexActionMap[ccToKey(unitHexes[unit["id"]].cc)] = {
            index: idx,
            target: {
              index: targetIdx,
            },
          };
        }
      } else if (option["targetProfile"]["type"] == "OneOfHexes") {
        // console.log("hexes");

        for (const [targetIdx, cc] of option["targetProfile"]["values"][
          "options"
        ].entries()) {
          hexActionMap[ccToKey(cc)] = {
            index: idx,
            target: {
              index: targetIdx,
            },
          };
        }
      }
    }
  }

  console.log(hexActionMap);

  gameState.map.hexes.forEach((hexData) => {
    let realHexPosition = addRCs(CCToRC(hexData.cc), center);

    const hexContainer = new Container();
    map.addChild(hexContainer);

    const terrainSprite = new Sprite(textureMap[hexData.terrain]);
    terrainSprite.anchor = 0.5;

    let hex = new Graphics(
      hexData.visible ? visibleHexShape : invisibleHexShape,
    );
    hexContainer.position = realHexPosition;

    let hexMask = new Graphics(fullHexShape);

    hexContainer.addChild(hexMask);
    terrainSprite.mask = hexMask;
    hexContainer.addChild(terrainSprite);

    hexContainer.addChild(hex);

    // hex.zIndex = 0;
    // terrainSprite.zIndex = 0;
    //
    // terrainSprite.mask = hex;

    // hexContainer.addChild(hex);

    const label = new Text({
      text: `${hexData.cc.r},${hexData.cc.h}\n${hexDistance({ r: 0, h: 0 }, hexData.cc)}`,
      style: smallTextStyle,
    });
    label.anchor = 0.5;
    hexContainer.addChild(label);

    if (hexData.unit) {
      const unitContainer = new Container();
      const unitSprite = new Sprite(textureMap[hexData.unit.blueprint]);
      unitSprite.anchor = 0.5;
      // unitSprite.scale = sizeMap[hexData.unit.size];
      if (hexData.unit.controller != gameState.player) {
        unitSprite.scale.x = -unitSprite.scale.x;
      }

      unitContainer.addChild(unitSprite);

      const healthText = new Text({
        text: `${hexData.unit.maxHealth - hexData.unit.damage}/${hexData.unit.maxHealth}`,
        style: healthTextStyle,
      });
      healthText.anchor = { x: 1, y: 0 };
      healthText.position = {
        x: unitSprite.width / 2 - 3,
        y: -unitSprite.height / 2 + 3,
      };
      unitContainer.addChild(healthText);

      if (
        gameState.activeUnitContext &&
        gameState.activeUnitContext.unit.id == hexData.unit.id
      ) {
        const movementPoints = new Text({
          text: `${gameState.activeUnitContext.movementPoints}`,
          style: largeTextStyle,
        });
        movementPoints.anchor = 0.5;
        unitContainer.addChild(movementPoints);
      }

      const graphics = new Graphics()
        .setStrokeStyle({
          color: hexData.unit.controller != gameState.player ? "red" : "green",
          width: 3,
        })
        .rect(-60, -74, 120, 148)
        .stroke();
      // graphics.scale = sizeMap[hexData.unit.size];
      unitContainer.addChild(graphics);

      if (hexData.unit.exhausted) {
        unitContainer.angle = 90;
      }

      unitContainer.scale = sizeMap[hexData.unit.size];

      hexContainer.addChild(unitContainer);
    }

    if (ccToKey(hexData.cc) in hexActionMap) {
      const frameGraphic = new Graphics(selectableFrame);
      hexContainer.addChild(frameGraphic);
      frameGraphic.zIndex = 1;
    }

    hexContainer.eventMode = "static";
    hexContainer.on("pointerdown", (event) => {
      console.log("click", event.button);
      if (event.button == 0 && ccToKey(hexData.cc) in hexActionMap) {
        gameConnection.send(JSON.stringify(hexActionMap[ccToKey(hexData.cc)]));
      }
    });
  });

  return map;
};

async function main() {
  const app = new Application();
  await app.init({ resizeTo: window, antialias: false });
  document.body.appendChild(app.canvas);

  let map = new Container();

  app.stage.addChild(map);

  let applicationState: ApplicationState = {
    shouldRerender: false,
    gameState: null,
    gameObjectDetails: null,
  };

  fetch('http://localhost:8000/game-object-details').then(
      async response => {
        let jsonResponse = recursiveCamelCase(await response.json());

        for (const [identifier, unitDetails] of Object.entries(jsonResponse.units)) {
          textureMap[unitDetails.identifier] = await Assets.load(unitDetails.smallImage);
        }

        for (const [identifier, terrainDetails] of Object.entries(jsonResponse.terrain)) {
          textureMap[terrainDetails.identifier] = await Assets.load(terrainDetails.image)
        }

          applicationState.gameObjectDetails = jsonResponse;

      }
  )


  const gameConnection = new WebSocket("ws://localhost:8765/ws");
  gameConnection.onmessage = (event) => {
    // console.log(event.data);
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

  app.ticker.add((ticker) => {
    if (applicationState.shouldRerender && applicationState.gameState && applicationState.gameObjectDetails) {
      app.stage.removeChild(map);
      map = renderMap(app, applicationState.gameState, applicationState.gameObjectDetails, gameConnection);
      app.stage.addChild(map);
      applicationState.shouldRerender = false;
    }
    map.position = worldTranslation;
    map.scale = worldScale;
  });
}

await main();
