import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Text,
  TextStyle,
} from "pixi.js";
import { CC, GameState } from "./interfaces/gameState.ts";
// import type { PointData } from "pixi.js/lib/maths/point/PointData";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";

const hexSize = 45;

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

const renderMap = (app: Application, gameState: GameState): Container => {
  // TODO this shouldn't be here
  let maxX = window.innerWidth;
  let maxY = window.innerHeight;
  let center = { x: maxX / 2, y: maxY / 2 };

  // TODO not here
  const getHexShape = (color: FillInput): GraphicsContext => {
    let hexShape = new GraphicsContext()
      .setStrokeStyle({ color: "red", pixelLine: true })
      .moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath().fill(color);
    hexShape.stroke();
    return hexShape;
  };
  const visibleHexShape = getHexShape("447744");
  const invisibleHexShape = getHexShape("black");

  // TODO not here
  const smallTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 12,
    fill: 0xff1010,
    align: "center",
  });

  // TODO
  // app.stage.removeChild(map);
  const map = new Container();

  app.stage.addChild(map);

  gameState.map.hexes.forEach((hexData) => {
    let realHexPosition = addRCs(CCToRC(hexData.cc), center);

    const hexContainer = new Container();
    map.addChild(hexContainer);

    let hex = new Graphics(
      hexData.visible ? visibleHexShape : invisibleHexShape,
    );
    hexContainer.addChild(hex);
    hexContainer.position = realHexPosition;

    const label = new Text({
      text: `${hexData.cc.r},${hexData.cc.h}\n${hexDistance({ r: 0, h: 0 }, hexData.cc)}`,
      style: smallTextStyle,
    });
    label.anchor = 0.5;
    hexContainer.addChild(label);

    hexContainer.zIndex = 0;
  });

  return map;
};
