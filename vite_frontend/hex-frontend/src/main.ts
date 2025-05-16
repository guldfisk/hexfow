import "./style.css";

import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Text,
  TextStyle,
} from "pixi.js";
import type { PointData } from "pixi.js/lib/maths/point/PointData";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";

type HexCoord = { r: number; h: number };
export type CubeHexCoord = HexCoord & { l: number };

const hexSize = 45;

const enum CollisionType {
  FULL,
  LEFT_CORNER,
  RIGHT_CORNER,
}

const hexWidth = Math.sqrt(3) * hexSize;
const hexHeight = hexSize * 2;

const hexVerts: [number, number][] = [
  [hexWidth / 2, -hexSize / 2],
  [0, -hexSize],
  [-hexWidth / 2, -hexSize / 2],
  [-hexWidth / 2, hexSize / 2],
  [0, hexHeight / 2],
  [hexWidth / 2, hexSize / 2],
];

const hexPoints: { x: number; y: number }[] = hexVerts.map(([x, y]) => ({
  x,
  y,
}));

const addHexPoints = (a: HexCoord, b: HexCoord): HexCoord => ({
  r: a.r + b.r,
  h: a.h + b.h,
});

const hexToPixelCoord = (hexCoord: HexCoord): PointData => ({
  x: hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  y: hexSize * ((3 / 2) * hexCoord.r),
});

const unrollPoint = (point: PointData): [number, number] => [point.x, point.y];

const addPointData = (a: PointData, b: PointData): PointData => ({
  x: a.x + b.x,
  y: a.y + b.y,
});
const scalarMultPoint = (p: PointData, s: number): PointData => ({
  x: p.x * s,
  y: p.y * s,
});

const range = (
  first: number,
  second: number | undefined = undefined,
): number[] =>
  second == undefined
    ? [...Array(first).keys()]
    : [...Array(-first + second).keys()].map((v) => v + first);

const hexDirections: HexCoord[] = [
  { r: -1, h: 1 },
  { r: 0, h: 1 },
  { r: 1, h: 0 },
  { r: 1, h: -1 },
  { r: 0, h: -1 },
  { r: -1, h: 0 },
];

const edgeCollisionDirections: [HexCoord, [HexCoord, HexCoord]][] = range(
  6,
).map((i) => [
  addHexPoints(hexDirections[i], hexDirections[(i + 1) % 6]),
  [hexDirections[i], hexDirections[(i + 1) % 6]],
]);

const isLeft = (
  lineFrom: PointData,
  lineTo: PointData,
  point: PointData,
): number =>
  // (lineTo.x - lineFrom.x) * (point.y - lineFrom.y) - (lineTo.y - lineFrom.y) * (point.x - lineFrom.x) > 0
  // (lineTo.x - lineFrom.x) * (point.y - lineFrom.y) -
  //   (lineTo.y - lineFrom.y) * (point.x - lineFrom.x) >
  // 0
  (lineTo.x - lineFrom.x) * (point.y - lineFrom.y) -
  (lineTo.y - lineFrom.y) * (point.x - lineFrom.x);

const collides = (
  lineFrom: PointData,
  lineTo: PointData,
  shape: PointData[],
): boolean => {
  let seenLeft = false;
  let seenRight = false;
  for (const point of shape) {
    const v = isLeft(lineFrom, lineTo, point);
    if (v == 0) {
      return true;
    }
    if (v > 0) {
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

const getCheckDirectionsForCartesian = (
  fromPoint: PointData,
  toPoint: PointData,
): HexCoord[] => {
  if (toPoint.x > fromPoint.x) {
    if (toPoint.y < fromPoint.y) {
      return [
        { r: -1, h: 0 },
        { r: -1, h: 1 },
        { r: 0, h: 1 },
      ];
    } else {
      return [
        { r: 0, h: 1 },
        { r: 1, h: 0 },
        { r: 1, h: -1 },
      ];
    }
  } else {
    if (toPoint.y < fromPoint.y) {
      return [
        { r: 0, h: -1 },
        { r: -1, h: 0 },
        { r: -1, h: 1 },
      ];
    } else {
      return [
        { r: 0, h: -1 },
        { r: 1, h: -1 },
        { r: 1, h: 0 },
      ];
    }
  }
};

const getCheckDirections = (
  fromCoord: HexCoord,
  toCoord: HexCoord,
): HexCoord[] => {
  const realFrom = hexToPixelCoord(fromCoord);
  const realTo = hexToPixelCoord(toCoord);

  return getCheckDirectionsForCartesian(realFrom, realTo);
};

const findCartesianCollisions = (
  lineFrom: HexCoord,
  lineTo: HexCoord,
): [HexCoord, CollisionType][] => {
  const collisions: [HexCoord, CollisionType][] = [];
  const directions = getCheckDirections(lineFrom, lineTo);
  const realFrom = hexToPixelCoord(lineFrom);
  const realTo = hexToPixelCoord(lineTo);

  let currentChecking = lineFrom;
  let checkingNext = lineFrom;

  while (!(currentChecking.r == lineTo.r && currentChecking.h == lineTo.h)) {
    for (const direction of directions) {
      const position = {
        r: currentChecking.r + direction.r,
        h: currentChecking.h + direction.h,
      };
      const checkingRealPosition = hexToPixelCoord(position);
      if (
        collides(
          realFrom,
          realTo,
          hexVerts.map(([x, y]) => ({
            // LMAO
            x: checkingRealPosition.x + x * 1.01,
            y: checkingRealPosition.y + y * 1.01,
          })),
        )
      ) {
        if (
          collides(
            realFrom,
            realTo,
            hexVerts.map(([x, y]) => ({
              // LMAO
              x: checkingRealPosition.x + x * 0.99,
              y: checkingRealPosition.y + y * 0.99,
            })),
          )
        ) {
          collisions.push([position, CollisionType.FULL]);
          checkingNext = position;
        } else {
          collisions.push([
            position,
            CollisionType.FULL,
            // isLeft(realFrom, realTo, checkingRealPosition) > 0
            //   ? CollisionType.LEFT_CORNER
            //   : CollisionType.RIGHT_CORNER,
          ]);
        }
      }
    }
    currentChecking = checkingNext;
  }
  return collisions;
};

const findCollisions = (
  lineFrom: HexCoord,
  lineTo: HexCoord,
): [HexCoord, CollisionType][][] => {
  const relativeTo = { r: lineTo.r - lineFrom.r, h: lineTo.h - lineFrom.h };
  for (const [{ r, h }, backwards] of edgeCollisionDirections) {
    if (
      r > 0 == relativeTo.r > 0 &&
      h > 0 == relativeTo.h > 0 &&
      (r == 0
        ? relativeTo.h % h == 0
        : h == 0
          ? relativeTo.r % r == 0
          : relativeTo.r / r == relativeTo.h / h && relativeTo.r % r == 0)
    ) {
      return range(
        1,
        (r > 0 ? relativeTo.r / r : relativeTo.h / h) + 1,
      ).flatMap((i) => [
        backwards.map((b) => [
          {
            r: r * i + lineFrom.r - b.r,
            h: h * i + lineFrom.h - b.h,
          },
          CollisionType.FULL,
        ]),
        [
          [
            { r: r * i + lineFrom.r, h: h * i + lineFrom.h },
            CollisionType.FULL,
          ],
        ],
      ]);
    }
  }
  return findCartesianCollisions(lineFrom, lineTo).map((h) => [h]);
};

const hasEdgeCollisions = (lineTo: HexCoord): boolean => {
  const relativeTo = lineTo;
  for (const [{ r, h }, backwards] of edgeCollisionDirections) {
    if (
      r > 0 == relativeTo.r > 0 &&
      h > 0 == relativeTo.h > 0 &&
      (r == 0
        ? relativeTo.h % h == 0
        : h == 0
          ? relativeTo.r % r == 0
          : relativeTo.r / r == relativeTo.h / h && relativeTo.r % r == 0)
    ) {
      return true;
    }
  }
  return false;
};
// edgeCollisionDirections.some(
//   ([{ r, h }]) =>
//     r > 0 == p.r > 0 &&
//     h > 0 == p.h > 0 &&
//     (r == 0
//       ? p.h % h == 0
//       : h == 0
//         ? p.r % r == 0
//         : p.r / r == p.h / h && p.r % r == 0),
//   // (r == 0 ? p.r == 0 : p.r != 0 && (r > 0 == p.r > 0) && p.r % r == 0) &&
//   // (h == 0 ? p.h == 0 : p.h !== 0 && (h > 0 == p.h > 0) && p.h % h == 0),
// );

const findCollisionsFromVertToVert = (
  lineFrom: HexCoord,
  fromVertIndex: number,
  lineTo: HexCoord,
  toVertIndex: number,
): HexCoord[] => {
  const collisions: HexCoord[] = [];
  const realFrom = addPointData(
    hexToPixelCoord(lineFrom),
    scalarMultPoint(hexPoints[fromVertIndex], 0.98),
  );
  const realTo = addPointData(
    hexToPixelCoord(lineTo),
    scalarMultPoint(hexPoints[toVertIndex], 0.98),
  );
  const directions = getCheckDirectionsForCartesian(realFrom, realTo);

  let currentChecking = lineFrom;
  let checkingNext = lineFrom;

  let count = 0;

  while (!(currentChecking.r == lineTo.r && currentChecking.h == lineTo.h)) {
    for (const direction of directions) {
      const position = {
        r: currentChecking.r + direction.r,
        h: currentChecking.h + direction.h,
      };
      const checkingRealPosition = hexToPixelCoord(position);
      if (
        collides(
          realFrom,
          realTo,
          hexVerts.map(([x, y]) => ({
            x: checkingRealPosition.x + x * 0.95,
            y: checkingRealPosition.y + y * 0.95,
          })),
        )
      ) {
        collisions.push(position);
        checkingNext = position;
      }
    }
    currentChecking = checkingNext;
    count += 1;
    if (count > 100) {
      break;
    }
  }
  return collisions;
};

const hexDistance = (fromCoord: HexCoord, toCoord: HexCoord): number => {
  const r = fromCoord.r - toCoord.r;
  const h = fromCoord.h - toCoord.h;
  // return Math.max(r, h, -(r + h));
  return (Math.abs(r) + Math.abs(r + h) + Math.abs(h)) / 2;
};

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
  const wallHexShape = getHexShape("444444");
  const visibleHexShape = getHexShape("447744");
  const invisibleHexShape = getHexShape("black");

  const hexMapRadius = 10;
  const hexCoords = range(-hexMapRadius, hexMapRadius + 1)
    .flatMap((r) =>
      range(-hexMapRadius, hexMapRadius + 1).map((h) => ({
        r,
        h,
      })),
    )
    .filter(
      (p) => -hexMapRadius <= -(p.r + p.h) && -(p.r + p.h) <= hexMapRadius,
    );

  const walls = new Map();

  const hashCoord = (p: HexCoord) => `${p.r},${p.h}`;

  const getIsWall = (p: HexCoord) => walls.get(hashCoord(p));
  const setIsWall = (p: HexCoord, isWall: boolean) =>
    walls.set(hashCoord(p), isWall);

  hexCoords.forEach((p) => setIsWall(p, false));

  let lines: [HexCoord, HexCoord][] = [];

  const isBlocked = (lineFrom: HexCoord, lineTo: HexCoord): boolean => {
    const collidedSides = [false, false];
    const collidedCorners = [false, false];
    for (const hexes of findCollisions(lineFrom, lineTo)) {
      if (hexes.length == 1 && getIsWall(hexes[0][0])) {
        if (hexes[0][1] == CollisionType.FULL) {
          return true;
        } else {
          collidedCorners[hexes[0][1] == CollisionType.LEFT_CORNER ? 0 : 1] =
            true;
          if (collidedCorners.every((v) => v)) {
            return true;
          }
        }
      }
      if (hexes.length == 2) {
        for (const i of range(2)) {
          if (getIsWall(hexes[i][0])) {
            collidedSides[i] = true;
          }
        }
        if (collidedSides.every((v) => v)) {
          return true;
        }
      }
    }
    return false;
  };

  let openLine: HexCoord | null = null;
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
  let shouldRerender = true;

  const renderMap = (): void => {
    // if (!shouldRerender) {return}
    app.stage.removeChild(map);
    map = new Container();

    app.stage.addChild(map);

    let linePointsToReal = addPointData(hexToPixelCoord(linePointsTo), center);

    // const directions = getCheckDirections({ r: 0, h: 0 }, linePointsTo);
    const collisions = findCollisions({ r: 0, h: 0 }, { r: -10, h: 5 });
    // const vertCollisions = findCollisionsFromVertToVert(
    //   { r: 0, h: 0 },
    //   5,
    //   linePointsTo,
    //   4,
    // );

    // console.log(collisions);

    // console.log("added");

    hexCoords.forEach((p) => {
      let realHexPosition = addPointData(hexToPixelCoord(p), center);
      // console.log(hexCoords.filter(c => c == {r: 0, h: 0}))
      // console.log(p)

      const hexContainer = new Container();
      map.addChild(hexContainer);

      // console.log(findCollisions({ r: 0, h: 0 }, p).map((h) => walls.get(h)))
      // console.log(findCollisions({ r: 0, h: 0 }, p))

      let hex = new Graphics(
        // missesCollision({ r: 0, h: 0 }, p)
        //   ? invisibleHexShape
        //   : collisions.some((d) => d.r == p.r && d.h == p.h)
        //     ? highlightedHexShape
        //     : visibleHexShape,

        // getIsWall(p)
        //   ? wallHexShape
        //   : range(6)
        //         .flatMap((f) => range(6).map((s) => [f, s]))
        //         .some(
        //           ([f, s]) =>
        //             !findCollisionsFromVertToVert({ r: 0, h: 0 }, f, p, s).some(
        //               getIsWall,
        //             ),
        //         )
        //     ? visibleHexShape
        //     : invisibleHexShape,

        getIsWall(p)
          ? wallHexShape
          : // : isBlocked({ r: 0, h: 0 }, p)
            isBlocked(linePointsTo, p)
            ? invisibleHexShape
            : visibleHexShape,

        // getIsWall(p)
        //   ? wallHexShape
        //   : !findCollisions({ r: 0, h: 0 }, p).some((hexes) =>
        //         hexes.every(getIsWall),
        //       )
        //     ? visibleHexShape
        //     : invisibleHexShape,

        // vertCollisions.some((d) => d.r == p.r && d.h == p.h)
        //   ? highlightedHexShape
        //   : hexShape,

        // collisions.some(hexes => hexes.some(d => d.r == p.r && d.h == p.h))
        //   ? highlightedHexShape
        //   : hexShape,

        // hasEdgeCollisions(p) ? visibleHexShape : invisibleHexShape,
      );
      hexContainer.addChild(hex);
      hexContainer.position = realHexPosition;

      const label = new Text({
        text: `${p.r},${p.h}\n${hexDistance({ r: 0, h: 0 }, p)}`,
        style: smallTextStyle,
      });
      label.anchor = 0.5;
      // label.position = realHexPosition;
      hexContainer.addChild(label);

      hexContainer.eventMode = "static";
      hexContainer.zIndex = 0;

      hexContainer.on("pointerenter", () => {
        if (!(linePointsTo.r == p.r && linePointsTo.h == p.h)) {
          linePointsTo = p;
          shouldRerender = true;
        }
      });

      // hexContainer.on("pointerdown", () => {
      //   console.log("down", p);
      //   setIsWall(p, !getIsWall(p))
      //   shouldRerender = true;
      // });
      hexContainer.on("pointerdown", (event) => {
        console.log("click", event.button, p);

        if (event.button == 0) {
          setIsWall(p, !getIsWall(p));
          shouldRerender = true;
        } else if (event.button == 2) {
          if (openLine) {
            lines.push([p, openLine]);
            console.log(lines);
            openLine = null;
            shouldRerender = true;
          } else {
            const lengthBefore = lines.length;
            lines = lines.filter(
              (points) =>
                !points.some((point) => point.r == p.r && point.h == p.h),
            );
            if (lines.length == lengthBefore) {
              openLine = p;
            } else {
              shouldRerender = true;
            }
          }
        }
      });
    });

    // const f = 5;
    // const s = 4;
    // let line = new Graphics()
    //   .moveTo(...unrollPoint(addPointData(center, hexPoints[f])))
    //   .lineTo(...unrollPoint(addPointData(linePointsToReal, hexPoints[s])))
    //   .stroke({
    //     color: !findCollisionsFromVertToVert(
    //       { r: 0, h: 0 },
    //       f,
    //       linePointsTo,
    //       s,
    //     ).some(getIsWall)
    //       ? "blue"
    //       : "red",
    //     pixelLine: true,
    //   });
    // map.addChild(line);
    // line.eventMode = "none";

    // for (const f of range(6)) {
    //   for (const s of range(6)) {
    //     if (
    //       !findCollisionsFromVertToVert(
    //         { r: 0, h: 0 },
    //         f,
    //         linePointsTo,
    //         s,
    //       ).some(getIsWall)
    //     ) {
    //       console.log(f, s);
    //     }
    //     let line = new Graphics()
    //       .moveTo(...unrollPoint(addPointData(center, hexPoints[f])))
    //       .lineTo(...unrollPoint(addPointData(linePointsToReal, hexPoints[s])))
    //       .stroke({
    //         color: !findCollisionsFromVertToVert(
    //           { r: 0, h: 0 },
    //           f,
    //           linePointsTo,
    //           s,
    //         ).some(getIsWall)
    //           ? "blue"
    //           : "red",
    //         pixelLine: true,
    //       });
    //     map.addChild(line);
    //     line.eventMode = "none";
    //   }
    // }

    // for (const fromVertex of hexPoints) {
    //   for (const toVertex of hexPoints) {
    //     let line = new Graphics()
    //       .moveTo(...unrollPoint(addPointData(center, fromVertex)))
    //       .lineTo(...unrollPoint(addPointData(linePointsToReal, toVertex)))
    //       .stroke({
    //         color: !findCollisionsFromVertToVert({ r: 0, h: 0 }, f, p, s).some(
    //           getIsWall,
    //         )
    //           ? "white"
    //           : "blue",
    //         pixelLine: true,
    //       });
    //     map.addChild(line);
    //   }
    // }

    // let line = new Graphics()
    //   .moveTo(...unrollPoint(center))
    //   .lineTo(...unrollPoint(linePointsToReal))
    //   .stroke({ color: "white", pixelLine: true });
    // line.eventMode = "none";
    // map.addChild(line);

    for (const [_from, _to] of lines) {
      //       let line = new Graphics()
      //   .moveTo(...unrollPoint(center))
      //   .lineTo(...unrollPoint(linePointsToReal))
      //   .stroke({ color: "white", pixelLine: true });
      // line.eventMode = "none";
      // map.addChild(line);

      // console.log(hexToPixelCoord(_from));
      // console.log(hexToPixelCoord(_to));
      let line = new Graphics()
        .moveTo(...unrollPoint(addPointData(hexToPixelCoord(_from), center)))
        .lineTo(...unrollPoint(addPointData(hexToPixelCoord(_to), center)))
        .stroke({ color: "white", pixelLine: true });
      line.eventMode = "none";
      map.addChild(line);
      // console.log(hexToPixelCoord(_from));
      // console.log(hexToPixelCoord(_to));
      // let line = new Graphics()
      //   .moveTo(...unrollPoint(center))
      //   .lineTo(...unrollPoint(hexToPixelCoord(_to)))
      //   .stroke({ color: "white", pixelLine: true });
      // line.eventMode = "none";
      // map.addChild(line);
    }

    // console.log(linePointsTo);
    shouldRerender = false;
  };

  // renderMap();

  const overlayMap = new Container();
  overlayMap.zIndex = 2;

  let cursorBall = new Graphics().circle(0, 0, 20).fill("blue");
  overlayMap.addChild(cursorBall);
  // app.stage.addChild(overlayMap);

  let isDragging = false;

  app.stage.on("pointerdown", (event) => {
    console.log("global pointer down");
    if (event.button == 1) {
      isDragging = true;
    }
  });

  app.stage.on("pointerup", (event) => {
    // console.log(event.button);
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
    worldScale = worldScale * (1 + event.deltaY / -1000);
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
    if (shouldRerender) {
      renderMap();
    }
    elapsed += ticker.deltaTime;
    lastTenFrames = lastTenFrames.slice(-10).concat([ticker.elapsedMS]);
    fpsText.text = lastTenFrames.length
      ? 1000 / (lastTenFrames.reduce((a, b) => a + b, 0) / lastTenFrames.length)
      : 0;

    let linePointsToReal = addPointData(hexToPixelCoord(linePointsTo), center);

    // pointToText.text = JSON.stringify(linePointsTo);
    // pointToText.text =
    //   JSON.stringify(worldTranslation) + "\n" + JSON.stringify(worldScale);
    const slope =
      (linePointsToReal.y - center.y) / (linePointsToReal.x - center.x);

    pointToText.text = slope;

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
