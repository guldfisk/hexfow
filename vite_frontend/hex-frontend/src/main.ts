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
} from "pixi.js";
import type { PointData } from "pixi.js/lib/maths/point/PointData";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";

export type HexCoord = { r: number; h: number };
export type CubeHexCoord = HexCoord & { l: number };

const cardWidth = 140;
const cardHeight = 200;

const hexSize = 45;

// const hexWidth = hexSize * 2;
// const hexHeight = Math.sqrt(3) * hexSize;

const hexWidth = Math.sqrt(3) * hexSize;
const hexHeight = hexSize * 2;

// const hexVerts: [number, number][] = [
//   [hexSize, 0],
//   [hexSize / 2, -hexHeight / 2],
//   [-hexSize / 2, -hexHeight / 2],
//   [-hexSize, 0],
//   [-hexSize / 2, hexHeight / 2],
//   [hexSize / 2, hexHeight / 2],
// ];

const hexVerts: [number, number][] = [
  [hexWidth / 2, -hexSize / 2],
  [0, -hexSize],
  [-hexWidth / 2, -hexSize / 2],
  [-hexWidth / 2, hexSize / 2],
  [0, hexHeight / 2],
  [hexWidth / 2, hexSize / 2],
];

const hexToPixelCoord = (hexCoord: HexCoord): PointData => ({
  x: hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  y: hexSize * ((3 / 2) * hexCoord.r),
});

const unrollPoint = (point: PointData): [number, number] => [point.x, point.y];

const addPointData = (a: PointData, b: PointData): PointData => ({
  x: a.x + b.x,
  y: a.y + b.y,
});

const range = (first: number, second: number): number[] =>
  second == undefined
    ? [...Array(first).keys()]
    : [...Array(-first + second).keys()].map((v) => v + first);

// public bool isLeft(Point a, Point b, Point c) {
//   return (b.x - a.x)*(c.y - a.y) - (b.y - a.y)*(c.x - a.x) > 0;
// }

// position = sign((Bx - Ax) * (Y - Ay) - (By - Ay) * (X - Ax))

const isLeft = (
  lineFrom: PointData,
  lineTo: PointData,
  point: PointData,
): boolean =>
  // (lineTo.x - lineFrom.x) * (point.y - lineFrom.y) - (lineTo.y - lineFrom.y) * (point.x - lineFrom.x) > 0
  (lineTo.x - lineFrom.x) * (point.y - lineFrom.y) -
    (lineTo.y - lineFrom.y) * (point.x - lineFrom.x) >
  0;

const collides = (
  lineFrom: PointData,
  lineTo: PointData,
  shape: PointData[],
): boolean => {
  let seenLeft = false;
  let seenRight = false;
  for (const point of shape) {
    if (isLeft(lineFrom, lineTo, point)) {
      if (seenRight) {
        return true;
      }
      seenLeft = true;
    } else {
      if (seenLeft) {
        return true;
      }
      seenRight = true;
    }
  }
  return false;
};

// const findCollisions = (lineFrom: HexCoord, lineTo: HexCoord): HexCoord[] => {
//
// }

async function setupApp() {
  const app = new Application();
  await app.init({ resizeTo: window, antialias: false });
  // app.ticker.maxFPS = 2
  // console.log(app.ticker.speed)
  document.body.appendChild(app.canvas);

  // await Assets.load("https://pixijs.com/assets/bunny.png");
  // let sprite = Sprite.from("https://pixijs.com/assets/bunny.png");

  let maxX = window.innerWidth;
  let maxY = window.innerHeight;

  let center = { x: maxX / 2, y: maxY / 2 };

  const getHexShape = (color: FillInput): GraphicsContext => {
    let hexShape = new GraphicsContext()
      .setStrokeStyle({ color: "red", pixelLine: true })
      .moveTo(...hexVerts[0]);
    hexVerts.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath().fill(color);
    hexShape.stroke();
    return hexShape;
  };

  const hexShape = getHexShape("black");
  const highlightedHexShape = getHexShape("444444");

  let hexMapRadius = 10;
  let hexCoords = range(-hexMapRadius, hexMapRadius + 1)
    .flatMap((r) =>
      range(-hexMapRadius, hexMapRadius + 1).map((h) => ({ r, h })),
    )
    .filter(
      (p) => -hexMapRadius <= -(p.r + p.h) && -(p.r + p.h) <= hexMapRadius,
    );

  let linePointsTo = { r: 0, h: 0 };
  let worldTranslation = { x: 0, y: 0 };
  let worldScale = 1;

  let map = new Container();

  app.stage.addChild(map);

  const commonTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 24,
    fill: 0xff1010,
    align: "center",
  });
  const smallTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 12,
    fill: 0xff1010,
    align: "center",
  });

  const fpsText = new Text({
    text: "0",
    style: commonTextStyle,
  });
  fpsText.zIndex = 1;

  const pointToText = new Text({
    text: "0",
    style: commonTextStyle,
  });
  pointToText.y += 200;
  pointToText.zIndex = 1;

  app.stage.addChild(fpsText);
  app.stage.addChild(pointToText);

  let elapsed = 0.0;
  let lastTenFrames: number[] = [];

  // console.log(isLeft({ x: 0, y: 0 }, { x: 0, y: 1 }, { x: 1, y: 0 }));
  // console.log(isLeft({ x: 0, y: 0 }, { x: 0, y: 1 }, { x: -1, y: 0 }));
  //
  // console.log(isLeft({ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }));
  // console.log(isLeft({ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: -1 }));

  const renderMap = (): void => {
    app.stage.removeChild(map);
    map = new Container();

    app.stage.addChild(map);

    let linePointsToReal = addPointData(hexToPixelCoord(linePointsTo), center);

    hexCoords.forEach((p) => {
      let realHexPosition = addPointData(hexToPixelCoord(p), center);
      let hex = new Graphics(
        collides(
          center,
          linePointsToReal,
          hexVerts.map(([x, y]) => ({
            x: realHexPosition.x + x,
            y: realHexPosition.y + y,
          })),
        )
          ? // isLeft(center, linePointsToReal, realHexPosition)
            highlightedHexShape
          : hexShape,
      );
      map.addChild(hex);
      hex.position = realHexPosition;

      const label = new Text({ text: `${p.r},${p.h}`, style: smallTextStyle });
      label.anchor = 0.5;
      label.position = realHexPosition;
      map.addChild(label);

      hex.eventMode = "static";
      hex.zIndex = 0;
      hex.on("pointerenter", () => {
        // console.log(p);
        // linePointsTo = {x: hex.position.x, y: hex.position.y};
        linePointsTo = p;
        renderMap();
        // if (line) {
        //   map.removeChild(line);
        // }
        // line = new Graphics()
        //   .moveTo(...unrollPoint(center))
        //   .lineTo(...unrollPoint(hex.position))
        //   .stroke({ color: "white", pixelLine: true });
        // map.addChild(line);
      });
    });

    let line = new Graphics()
      .moveTo(...unrollPoint(center))
      .lineTo(...unrollPoint(linePointsToReal))
      .stroke({ color: "white", pixelLine: true });

    // line.zIndex = 1;

    // map.rotation=elapsed;

    map.addChild(line);

    // console.log(linePointsTo);
  };

  renderMap();

  const overlayMap = new Container();
  overlayMap.zIndex = 2;

  let cursorBall = new Graphics().circle(0, 0, 20).fill("blue");
  overlayMap.addChild(cursorBall);
  app.stage.addChild(overlayMap);

  let isDragging = false;

  app.stage.on("pointerdown", (event) => {
    console.log(event.button);
    if (event.button == 1) {
      isDragging = true;
    }
  });

  app.stage.on("pointerup", (event) => {
    console.log(event.button);
    if (event.button == 1) {
      isDragging = false;
    }
  });
  app.stage.on("pointermove", (event) => {
    // console.log(event.movement);
    // cursorBall.position = {x: event.screenX, y: event.screenY};
    cursorBall.position = {
      x: (event.x - worldTranslation.x) / worldScale,
      y: (event.y - worldTranslation.y) / worldScale,
    };

    if (isDragging) {
      worldTranslation = {
        x: worldTranslation.x + event.movementX,
        y: worldTranslation.y + event.movementY,
      };
    }
  });
  app.stage.on("wheel", (event) => {
    // console.log({ x: event.x, y: event.y });

    const oldScale = worldScale;
    worldScale = worldScale * (1 + event.deltaY /- 1000);
    const pointingAtBefore = {
      x: (event.x - worldTranslation.x) / oldScale,
      y: (event.y - worldTranslation.y) / oldScale,
    };
    const pointingAtNow = {
      x: (event.x - worldTranslation.x) / worldScale,
      y: (event.y - worldTranslation.y) / worldScale,
    };

    // console.log(event.x, event.y, oldScale - worldScale);
    // const positionClickedInWorld = {x: (event.x + worldTranslation.x) * worldScale}

    worldTranslation = {
      x: worldTranslation.x + ( pointingAtNow.x - pointingAtBefore.x) * worldScale,
      y: worldTranslation.y + (pointingAtNow.y - pointingAtBefore.y) * worldScale,
    };
  });
  app.stage.eventMode = "static";
  app.stage.hitArea = app.screen;

  app.ticker.add((ticker) => {
    elapsed += ticker.deltaTime;
    lastTenFrames = lastTenFrames.slice(-10).concat([ticker.elapsedMS]);
    fpsText.text = lastTenFrames.length
      ? 1000 / (lastTenFrames.reduce((a, b) => a + b, 0) / lastTenFrames.length)
      : 0;
    // pointToText.text = JSON.stringify(linePointsTo);
    pointToText.text = JSON.stringify(worldTranslation) + '\n' + JSON.stringify(worldScale);

    overlayMap.position = worldTranslation;
    overlayMap.scale = worldScale;

    map.position = worldTranslation;
    map.scale = worldScale;

    // if (line) {
    //   map.removeChild(line);
    // }
    // line = new Graphics()
    //   .moveTo(...unrollPoint(center))
    //   .lineTo()
    //   .stroke({ color: "white", pixelLine: true });
    // map.addChild(line);
  });
}

await setupApp();
