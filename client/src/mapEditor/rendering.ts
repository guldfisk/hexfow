import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Sprite,
  Text,
  TextStyle,
} from "pixi.js";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";
import { MapEditorState, setHoveredHex, store } from "./state/store.ts";
import {
  addRCs,
  asUnitVector,
  ccToRC,
  constMultRC,
  getHexDimensions,
  getHexVerticeOffsets,
  hexSize,
  hexVerticeOffsets,
  rcToCC,
  subRCs,
} from "../game/geometry.ts";
import type { ColorSource } from "pixi.js/lib/color/Color";
import { getTexture, textureMap } from "./textures.ts";
import moize from "moize";

const colors = {
  enemy: "0x9b1711",
  ally: "0x2f71e7",
  buff: "0x3fab48",
  debuff: "ab3f89",
  neutralStatus: "757575",
  fullHealth: [237, 10, 10],
  noHealth: [22, 3, 1],
  fullEnergy: [47, 103, 248],
  noEnergy: [5, 17, 74],
};

const getHexMask = (color: FillInput, hexSize: number): GraphicsContext => {
  const hexVerticeOffsets = getHexVerticeOffsets(hexSize);
  let hexShape = new GraphicsContext().moveTo(...hexVerticeOffsets[0]);
  hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
  hexShape.closePath();
  hexShape.fill(color);
  return hexShape;
};
const getHexBorder = moize(
  (color: FillInput, hexSize: number): GraphicsContext => {
    const hexVerticeOffsets = getHexVerticeOffsets(hexSize);
    let hexShape = new GraphicsContext().moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath();
    hexShape.stroke({ color, width: 5 });
    return hexShape;
  },
);

const hexStatusFrame = getHexMask({ alpha: 0 }, 22);

const makeStatusIndicator = (status: string): Container => {
  const statusContainer = new Container();
  const statusSprite = new Sprite(getTexture("status", status));

  statusSprite.anchor = 0.5;
  statusContainer.addChild(statusSprite);

  const mask = new Graphics(hexStatusFrame);
  statusContainer.addChild(mask);
  statusSprite.mask = mask;

  return statusContainer;
};

export const renderMap = (
  app: Application,
  state: MapEditorState,
): Container => {
  // TODO this shouldn't be here
  let maxX = window.innerWidth;
  let maxY = window.innerHeight;
  let center = { x: maxX / 2, y: maxY / 2 };

  // TODO not here
  const getHexShape = (color: ColorSource): GraphicsContext => {
    let hexShape = new GraphicsContext()
      .setStrokeStyle({ color: color, pixelLine: true })
      .moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath().fill({ alpha: 0 }).stroke();
    return hexShape;
  };
  const getHexMask = (color: FillInput, hexSize: number): GraphicsContext => {
    const hexVerticeOffsets = getHexVerticeOffsets(hexSize);
    let hexShape = new GraphicsContext().moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath();
    hexShape.fill(color);
    return hexShape;
  };

  const visibleHexShape = getHexShape("grey");
  const hexMaskShape = getHexMask({ alpha: 0 }, hexSize);

  // TODO not here
  const smallTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 12,
    fill: 0xff1010,
    align: "center",
  });

  const map = new Container();

  app.stage.addChild(map);

  for (const spec of Object.values(state.mapData)) {
    let realHexPosition = addRCs(ccToRC(spec.cc), center);

    const hexContainer = new Container();
    map.addChild(hexContainer);
    hexContainer.position = realHexPosition;

    let hex = new Graphics(visibleHexShape);

    const terrainSprite = new Sprite(textureMap[spec.terrainType]);
    terrainSprite.anchor = 0.5;

    let hexMask = new Graphics(hexMaskShape);
    hexContainer.addChild(hexMask);

    // TODO this works apparently, but is it the correct way to do it??
    hexContainer.mask = hexMask;

    hexContainer.addChild(terrainSprite);
    hexContainer.addChild(hex);

    const label = new Text({
      text: `${spec.cc.r},${spec.cc.h}`,
      style: smallTextStyle,
    });
    label.anchor = 0.5;
    label.y = hexSize / 2 + 25;
    hexContainer.addChild(label);

    if (spec.unit) {
      const unitSprite = new Sprite(getTexture("unit", spec.unit.identifier));
      unitSprite.anchor = 0.5;

      const borderWith = 4;

      let graphics = new Graphics()
        .rect(
          -unitSprite.width / 2 - borderWith,
          -unitSprite.height / 2 - borderWith,
          unitSprite.width + borderWith * 2,
          unitSprite.height + borderWith * 2,
        )
        .fill(spec.unit.allied ? colors.ally : colors.enemy);

      hexContainer.addChild(graphics);
      hexContainer.addChild(unitSprite);
    }

    if (spec.isObjective) {
      const flagSprite = new Sprite(textureMap["flag_icon"]);
      flagSprite.anchor = 0.5;
      hexContainer.addChild(flagSprite);
    }

    for (const [idx, status] of spec.statuses.entries()) {
      const statusContainer = makeStatusIndicator(status);

      const smallerSize = hexSize - 30;
      const [smallerWidth, smallerHeight] = getHexDimensions(smallerSize);

      const firstPoint = { x: 0, y: -smallerHeight / 2 };
      const lastPoint = { x: smallerWidth / 2, y: -smallerSize / 2 };

      statusContainer.position = addRCs(
        firstPoint,
        constMultRC(
          asUnitVector(subRCs(lastPoint, firstPoint)),
          spec.statuses.length <= 4
            ? idx * 43
            : (hexSize / spec.statuses.length) * idx,
        ),
      );

      hexContainer.addChild(statusContainer);
    }
  }

  for (const spec of Object.values(state.mapData)) {
    if (spec.deploymentZoneOf != null) {
      let hex = new Graphics(
        getHexBorder(
          spec.deploymentZoneOf === 0 ? colors.ally : colors.enemy,
          hexSize,
        ),
      );
      hex.position = addRCs(ccToRC(spec.cc), center);
      map.addChild(hex);
    }
  }

  map.eventMode = "static";
  map.on("globalpointermove", (event) => {
    const positionOnMap = subRCs(map.toLocal(event.global), center);
    const cc = rcToCC(positionOnMap);
    store.dispatch(setHoveredHex(cc));
  });

  return map;
};
