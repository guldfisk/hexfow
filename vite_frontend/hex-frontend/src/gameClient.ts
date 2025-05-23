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
import { CC, GameState } from "./interfaces/gameState.ts";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";
import { ApplicationState } from "./interfaces/applicationState.ts";
import { recursiveCamelCase } from "./utils/case.ts";

import chickenImageUrl from "./images/chicken_small.png";
import pillarImageUrl from "./images/pillar_small.png";
import archerImageUrl from "./images/archer_small.png";

import forestImageUrl from "./images/terrain_forest_square.png";

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

const textureMap: { [key: string]: Texture } = {};

const renderMap = (
  app: Application,
  gameState: GameState,
  gameConnection: WebSocket,
): Container => {
  // TODO this shouldn't be here
  let maxX = window.innerWidth;
  let maxY = window.innerHeight;
  let center = { x: maxX / 2, y: maxY / 2 };
  //
  // console.log("rendering", gameState);

  // document.body.appendChild(app.canvas);
  document.getElementById("event-log").replaceChildren(
    ...gameState.eventLog.map((log) => {
      const element = document.createElement("p");
      element.textContent = log;
      return element;
    }),
  );
  // document

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
    hexShape.stroke();
    return hexShape;
  };
  // const visibleHexShape = getHexShape("447744");
  // const invisibleHexShape = getHexShape("black");
  const visibleHexShape = getHexShape({ color: "447744", alpha: 0 });
  const invisibleHexShape = getHexShape({ color: "black", alpha: 100 });
  const fullHexShape = getHexShape("red");

  // TODO not here
  const smallTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 12,
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

  gameState.map.hexes.forEach((hexData) => {
    let realHexPosition = addRCs(CCToRC(hexData.cc), center);

    const hexContainer = new Container();
    map.addChild(hexContainer);

    const terrainSprite = new Sprite(textureMap["forest"]);
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

      unitContainer.addChild(unitSprite);

      if (
        gameState.activeUnitContext &&
        gameState.activeUnitContext.unit.id == hexData.unit.id
      ) {
        const graphics = new Graphics()
          .setStrokeStyle({ color: "red", width: 3 })
          .rect(-60, -74, 120, 148)
          .stroke();
        unitContainer.addChild(graphics);
        const movementPoints = new Text({
          text: `${gameState.activeUnitContext.movementPoints}`,
          style: largeTextStyle,
        });
        movementPoints.anchor = 0.5;
        unitContainer.addChild(movementPoints);
      }

      // unitContainer.pivot = { x: 60, y: 74 };

      if (hexData.unit.exhausted) {
        unitContainer.angle = 90;
      }

      hexContainer.addChild(unitContainer);
    }

    hexContainer.eventMode = "static";
    hexContainer.on("pointerdown", (event) => {
      console.log("click", event.button);
      if (gameState.decision) {
        if (gameState.decision["explanation"] === "activate unit?") {
          // gameConnection.send(
          //   JSON.stringify({ index: 0, target: { index: 0 } }),
          // );
          if (hexData.unit) {
            const clickedIndex = gameState.decision["payload"]["options"][0][
              "targetProfile"
            ]["values"]["units"].findIndex((v) => v.id == hexData.unit.id);
            if (clickedIndex > -1) {
              gameConnection.send(
                JSON.stringify({
                  index: 0,
                  target: {
                    index: clickedIndex,
                  },
                }),
              );
            }
          }
        } else {
          const clickedIndex = gameState.decision["payload"]["options"][0][
            "targetProfile"
          ]["values"]["options"].findIndex(
            (v) => v.r == hexData.cc.r && v.h == hexData.cc.h,
          );
          if (clickedIndex > -1) {
            gameConnection.send(
              JSON.stringify({
                index: 0,
                target: {
                  index: clickedIndex,
                },
              }),
            );
          }
        }
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
    shouldRerender: true,
    gameState: {
      round: 1,
      map: {
        hexes: [
          {
            cc: { r: 0, h: 0 },
            terrain: "ground",
            visible: true,
            unit: null,
          },
        ],
      },
      eventLog: [],
      decision: {},
      activeUnitContext: null,
    },
  };

  textureMap["Chicken"] = await Assets.load(chickenImageUrl);
  textureMap["Lumbering Pillar"] = await Assets.load(pillarImageUrl);
  textureMap["Light Archer"] = await Assets.load(archerImageUrl);

  textureMap["forest"] = await Assets.load(forestImageUrl);

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

  // YIKES
  document.oncontextmenu = document.body.oncontextmenu = function () {
    return false;
  };

  app.ticker.add((ticker) => {
    if (applicationState.shouldRerender) {
      app.stage.removeChild(map);
      map = renderMap(app, applicationState.gameState, gameConnection);
      app.stage.addChild(map);
      applicationState.shouldRerender = false;
    }
    map.position = worldTranslation;
    map.scale = worldScale;
  });
}

await main();
