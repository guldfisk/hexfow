import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Sprite,
  Text,
  TextStyle,
  Texture,
} from "pixi.js";
import {
  GameState,
  Hex,
  Intention,
  Status,
  Unit,
  UnitStatus,
} from "../interfaces/gameState.ts";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";
import {
  addRCs,
  asUnitVector,
  ccEquals,
  ccToKey,
  ccToRC,
  constMultRC,
  getHexDimensions,
  getHexVerticeOffsets,
  hexHeight,
  hexSize,
  hexVerticeOffsets,
  hexWidth,
  rcEquals,
  rcInBox,
  rcToCC,
  subRCs,
} from "../geometry.ts";
import { getTexture, textureMap } from "./textures.ts";
import { range } from "./utils/range.ts";
import { AppState, deactivateMenu, hoverDetail, store } from "./state/store.ts";
import { getBaseActionSpace } from "./actions/actionSpace.ts";
import { selectionIcon } from "./actions/interface.ts";
import { menuActionSpacers } from "./actions/menues.ts";
import { HoveredDetails } from "../interfaces/details.ts";
import type { ColorSource } from "pixi.js/lib/color/Color";
import moize from "moize";
import { ViewContainer } from "pixi.js/lib/scene/view/ViewContainer";
import { CanvasTextOptions } from "pixi.js/lib/scene/text/Text";
import {
  makeAnimation,
  MapAnimation,
  shake,
  sigmoid,
} from "./animations/interface.ts";
import { CC, RC } from "../interfaces/geometry.ts";

const selectionIconMap: { [key in selectionIcon]: string } = {
  ranged_attack: "hex_selection_ranged_attack",
  melee_attack: "hex_selection_melee",
  activated_ability: "hex_selection_ability",
  generic: "hex_selection",
  aoe: "hex_selection_aoe",
  menu: "hex_selection_menu",
};

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

let maxX = window.innerWidth;
let maxY = window.innerHeight;
let center = { x: maxX / 2, y: maxY / 2 };

let previouslyHovered: string | null = null;

// TODO not here
const getHexShape = (color: FillInput): GraphicsContext => {
  let hexShape = new GraphicsContext()
    .setStrokeStyle({ color: "grey", pixelLine: true })
    .moveTo(...hexVerticeOffsets[0]);
  hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
  hexShape.closePath().fill(color).stroke();
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
const getDividerFrame = (num: number): GraphicsContext => {
  return new GraphicsContext()
    .rect(
      (-hexWidth + hexWidth * num) / 2,
      -hexHeight / 2,
      hexWidth / 2,
      hexHeight,
    )
    .fill({ alpha: 0 });
};

const getThreePartDividerFrame = (num: number) => {
  let hexShape = new GraphicsContext();
  range(3).map((i) => hexShape.lineTo(...hexVerticeOffsets[(i + num * 2) % 6]));
  hexShape.closePath().fill({ alpha: 0 });
  return hexShape;
};

const visibleHexShape = getHexShape({ color: "447744", alpha: 0 });
const invisibleHexShape = getHexShape({ color: "black", alpha: 100 });
const hexMaskShape = getHexMask({ alpha: 0 }, hexSize);
const highlightShape = getHexMask({ alpha: 0.5, color: "blue" }, hexSize);

const dividerFrames = [
  [hexMaskShape],
  [0, 1].map(getDividerFrame),
  [1, 0, 2].map(getThreePartDividerFrame),
];

const sizeIndicatorDiamondSize = 10;

const getSizeDiamondGraphicsContext = moize((color: FillInput) =>
  new GraphicsContext()
    .moveTo(0, -sizeIndicatorDiamondSize)
    .lineTo(sizeIndicatorDiamondSize, 0)
    .lineTo(0, sizeIndicatorDiamondSize)
    .lineTo(-sizeIndicatorDiamondSize, 0)
    .closePath()
    .fill(color),
);

const getFlagCapturedIndicator = moize((allied: boolean) =>
  new GraphicsContext()
    .circle(0, 0, 23)
    .fill(allied ? colors.ally : colors.enemy),
);

const statusFrame = new GraphicsContext().circle(0, 0, 20).fill({ alpha: 0 });
const diag = Math.sqrt(2) * 22;

const debuffStatusBorder = new Graphics()
  .circle(0, 0, 22)
  .moveTo(-diag / 2, diag / 2)
  .lineTo(0, diag)
  .lineTo(diag / 2, diag / 2)
  .closePath()
  .fill(colors.debuff);
const buffStatusBorder = new Graphics()
  .circle(0, 0, 22)
  .moveTo(-diag / 2, -diag / 2)
  .lineTo(0, -diag)
  .lineTo(diag / 2, -diag / 2)
  .closePath()
  .fill(colors.buff);
const neutralStatusBorder = new Graphics()
  .circle(0, 0, 22)
  .fill(colors.neutralStatus);

const intentionBorderMap = {
  buff: buffStatusBorder,
  neutral: neutralStatusBorder,
  debuff: debuffStatusBorder,
};

const hexStatusFrame = getHexMask({ alpha: 0 }, 22);
const hexStatusBorder = hexStatusFrame.stroke({
  color: "grey",
  pixelLine: true,
});

// TODO not here
const smallTextStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 12,
  fill: 0xff1010,
  align: "center",
});
const primaryHealthIndicatorTextStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 26,
  fill: "white",
  stroke: { color: "black", width: 2 },
  align: "center",
});
const secondaryHealthIndicatorTextStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 22,
  fill: "white",
  stroke: { color: "black", width: 2 },
  align: "center",
});
const largeTextStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 80,
  fill: "blue",
  align: "center",
  stroke: "white",
});
const durationStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 25,
  fill: "white",
  align: "center",
  stroke: { color: "black", width: 3 },
});
const stacksStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 25,
  fill: "black",
  align: "center",
  stroke: { color: "white", width: 3 },
});
const damageStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 50,
  fill: "black",
  align: "center",
  stroke: { color: "white", width: 3 },
});
const menuStyle = new TextStyle({
  fontFamily: "Arial",
  fontSize: 40,
  fill: "black",
  align: "center",
});

const unitWidth = 120;
const unitHeight = 148;
const borderWith = 4;
const arrowLength = 7;

const getUnitBackgroundGraphicsContext = moize((color: ColorSource) => {
  return new GraphicsContext()
    .moveTo(-unitWidth / 2 - borderWith, -unitHeight / 2 - borderWith)
    .lineTo(unitWidth / 2 + borderWith, -unitHeight / 2 - borderWith)
    .lineTo(unitWidth / 2 + borderWith + arrowLength, 0)
    .lineTo(unitWidth / 2 + borderWith, unitHeight / 2 + borderWith)
    .lineTo(-unitWidth / 2 - borderWith, unitHeight / 2 + borderWith)
    .closePath()
    .fill(color);
});

const getIndicatorBg = moize(
  (
    currentValue: number,
    maxValue: number,
    width: number,
    height: number,
    fromColor: number[],
    toColor: number[],
  ) => {
    const ratio = currentValue / maxValue;

    return new GraphicsContext()
      .roundRect(-width / 2, -height / 2, width, height, 6)
      .fill(
        fromColor.map((fv, i) => (fv * ratio + toColor[i] * (1 - ratio)) / 255),
      )
      .stroke({ color: "black", pixelLine: true });
  },
);

export const renderMap = (
  app: Application,
  state: AppState,
  gameState: GameState,
  makeDecision: (payload: { [key: string]: any }) => void,
): {
  map: Container;
  graphics: ViewContainer[];
  animations: MapAnimation[];
} => {
  const createdObjects: ViewContainer[] = [];
  const animations: MapAnimation[] = [];

  const newGraphic = (context: GraphicsContext) => {
    const g = new Graphics(context);
    createdObjects.push(g);
    return g;
  };

  const newSprite = (texture: Texture) => {
    const sprite = new Sprite(texture);
    createdObjects.push(sprite);
    return sprite;
  };

  const newText = (options?: CanvasTextOptions) => {
    const text = new Text(options);
    createdObjects.push(text);
    return text;
  };

  const makeStatusIndicator = (
    status: Status,
    intention: Intention | null,
  ): Container => {
    const statusContainer = new Container();
    const statusSprite = newSprite(getTexture("status", status.type));

    if (intention) {
      const frame = intentionBorderMap[intention];
      statusContainer.addChild(frame);
    }

    statusSprite.anchor = 0.5;
    statusContainer.addChild(statusSprite);

    const mask = newGraphic(!intention ? hexStatusFrame : statusFrame);
    statusContainer.addChild(mask);
    statusSprite.mask = mask;

    if (!intention) {
      const border = newGraphic(hexStatusBorder);
      statusContainer.addChild(border);
    }

    if (status.stacks) {
      const durationText = newText({
        text: `${status.stacks}`,
        style: stacksStyle,
      });
      durationText.x = -17;
      durationText.y = -7;
      durationText.anchor = 0.5;
      statusContainer.addChild(durationText);
    }

    if (status.duration) {
      const durationText = newText({
        text: `${status.duration}`,
        style: durationStyle,
      });
      durationText.x = 17;
      durationText.y = -7;
      durationText.anchor = 0.5;
      statusContainer.addChild(durationText);
    }

    return statusContainer;
  };

  const addStatuses = (
    from: (Status | UnitStatus)[] | null,
    to: (Status | UnitStatus)[],
    container: Container,
    positionGetter: (idx: number, count: number) => RC,
  ) => {
    if (from) {
      for (const [idx, status] of from.entries()) {
        if (!to.some((s) => s.type == status.type)) {
          const statusContainer = makeStatusIndicator(
            status,
            "intention" in status ? status.intention : null,
          );
          statusContainer.position = positionGetter(idx, from.length);

          container.addChild(statusContainer);

          animations.push(
            makeAnimation(
              (c) => (statusContainer.scale = 1 - c),
              200,
              sigmoid,
              () => container.removeChild(statusContainer),
            ),
          );
        }
      }
    }

    for (const [idx, status] of to.entries()) {
      const statusContainer = makeStatusIndicator(
        status,
        "intention" in status ? status.intention : null,
      );
      statusContainer.position = positionGetter(idx, to.length);

      container.addChild(statusContainer);

      if (from) {
        if (!from.some((s) => s.type == status.type)) {
          animations.push(
            makeAnimation(
              (c) => (statusContainer.scale = 1 + 3 * (1 - c)),
              250,
              sigmoid,
            ),
          );
        } else {
          const fromPosition = positionGetter(
            from.findIndex((s) => s.type == status.type),
            from.length,
          );
          const toPosition = positionGetter(idx, to.length);

          if (!rcEquals(fromPosition, toPosition)) {
            animations.push(
              makeAnimation(
                (c) =>
                  (statusContainer.position = addRCs(
                    constMultRC(toPosition, c),
                    constMultRC(fromPosition, 1 - c),
                  )),
                200,
                sigmoid,
              ),
            );
          }
        }
      }
    }
  };

  const map = new Container();

  app.stage.addChild(map);

  const actionSpace = (
    state.menuData
      ? menuActionSpacers[state.menuData.type](
          gameState,
          state.gameObjectDetails,
          makeDecision,
          state.menuData,
        )
      : getBaseActionSpace(
          gameState,
          makeDecision,
          state.gameObjectDetails,
          gameState.decision,
          gameState.active_unit_context,
          state.delayedActivation,
          state.actionFilter,
        )
  ).hexActions;

  const unitMoves: { [key: string]: { from: CC | null; to: CC | null } } = {};
  const unitRotations: { [key: string]: boolean } = {};
  const unitDamages: { [key: string]: number } = {};
  const statusChanges: {
    [key: string]: { from: UnitStatus[]; to: UnitStatus[] };
  } = {};
  const hexStatusChanges: {
    [key: string]: { from: Status[]; to: Status[] };
  } = {};

  const getUnitPositions = (gameState: GameState) => {
    const values: { [key: string]: { cc: CC; unit: Unit } } = {};
    for (const hexData of gameState.map.hexes) {
      if (hexData.unit) {
        values[hexData.unit.id] = { cc: hexData.cc, unit: hexData.unit };
      }
    }
    return values;
  };

  if (state.previousGameState && state.doAnimations) {
    const previousHexes: { [key: string]: Hex } = {};

    for (const hexData of state.previousGameState.map.hexes) {
      previousHexes[ccToKey(hexData.cc)] = hexData;
    }

    for (const hexData of gameState.map.hexes) {
      hexStatusChanges[ccToKey(hexData.cc)] = {
        from: previousHexes[ccToKey(hexData.cc)].statuses,
        to: hexData.statuses,
      };
    }

    const currentUnits = getUnitPositions(gameState);
    const previousUnits = getUnitPositions(state.previousGameState);
    for (const { cc, unit } of Object.values(currentUnits)) {
      if (
        unit.id in previousUnits &&
        !unit.is_ghost &&
        !previousUnits[unit.id].unit.is_ghost
      ) {
        const prevUnit = previousUnits[unit.id].unit;
        if (unit.damage != prevUnit.damage) {
          unitDamages[unit.id] = unit.damage - prevUnit.damage;
        }
        if (unit.exhausted != prevUnit.exhausted) {
          unitRotations[unit.id] = true;
        }
        statusChanges[unit.id] = { from: prevUnit.statuses, to: unit.statuses };
      }
      if (
        unit.id in previousUnits &&
        !ccEquals(cc, previousUnits[unit.id].cc)
      ) {
        unitMoves[unit.id] = { from: previousUnits[unit.id].cc, to: cc };
      }
      if (
        !(
          (gameState.active_unit_context &&
            gameState.active_unit_context.unit.id == unit.id) ||
          (state.previousGameState.active_unit_context &&
            state.previousGameState.active_unit_context.unit.id == unit.id) ||
          (unit.controller != gameState.player &&
            (!gameState.decision || !state.previousGameState.decision))
        )
      ) {
        continue;
      }
      if (unit.id in previousUnits) {
        if (unit.is_ghost && !previousUnits[unit.id].unit.is_ghost) {
          unitMoves[unit.id] = { from: cc, to: null };
        } else if (!unit.is_ghost && previousUnits[unit.id].unit.is_ghost) {
          unitMoves[unit.id] = { from: null, to: cc };
        }
      } else {
        if (unit.is_ghost) {
          unitMoves[unit.id] = { from: cc, to: null };
        } else {
          unitMoves[unit.id] = { from: null, to: cc };
        }
      }
    }
  }

  const actionTriggerZones: [Graphics[], RC][] = [];

  for (const hexData of gameState.map.hexes) {
    let realHexPosition = addRCs(ccToRC(hexData.cc), center);

    const hexContainer = new Container();
    map.addChild(hexContainer);

    const terrainSprite = newSprite(textureMap[hexData.terrain]);
    terrainSprite.anchor = 0.5;

    let hex = newGraphic(hexData.visible ? visibleHexShape : invisibleHexShape);
    hexContainer.position = realHexPosition;

    let hexMask = newGraphic(hexMaskShape);

    hexContainer.addChild(hexMask);

    // TODO this works apparently, but is it the correct way to do it??
    hexContainer.mask = hexMask;
    hexContainer.addChild(terrainSprite);

    hexContainer.addChild(hex);

    if (state.showCoordinates) {
      const coordinateLabel = newText({
        text: `${hexData.cc.r},${hexData.cc.h}`,
        style: smallTextStyle,
      });
      coordinateLabel.anchor = 0.5;
      coordinateLabel.y = hexSize / 2 + 25;
      hexContainer.addChild(coordinateLabel);
    }

    const hexActionTriggerZones = [];

    for (const [idx, action] of (ccToKey(hexData.cc) in actionSpace
      ? actionSpace[ccToKey(hexData.cc)].actions
      : []
    ).entries()) {
      const selectionSprite = newSprite(
        textureMap[selectionIconMap[action.type]],
      );
      selectionSprite.anchor = 0.5;
      selectionSprite.alpha = 0.75;
      hexContainer.addChild(selectionSprite);
      let mask = newGraphic(
        dividerFrames[actionSpace[ccToKey(hexData.cc)].actions.length - 1][idx],
      );
      hexContainer.addChild(mask);
      selectionSprite.mask = mask;

      let triggerZone = newGraphic(
        dividerFrames[actionSpace[ccToKey(hexData.cc)].actions.length - 1][idx],
      );
      triggerZone.eventMode = "static";
      triggerZone.on("pointerdown", (event) => {
        if (event.button == 0) {
          action.do(event.getLocalPosition(hexContainer));
        }
      });
      hexActionTriggerZones.push(triggerZone);
    }

    // TODO common trigger zone
    if (
      (state.delayedActivation ||
        state.actionFilter ||
        (state.menuData && !state.menuData.uncloseable)) &&
      !(actionSpace[ccToKey(hexData.cc)]?.actions || []).length
    ) {
      let triggerZone = newGraphic(dividerFrames[0][0]);
      triggerZone.eventMode = "static";
      triggerZone.on("pointerdown", (event) => {
        if (event.button == 0) {
          store.dispatch(deactivateMenu());
        }
      });
      hexActionTriggerZones.push(triggerZone);
    }

    if (hexData.is_objective) {
      const flagContainer = new Container();

      flagContainer.x = -hexWidth / 2 + 30;
      flagContainer.y = -hexSize / 2 + 20;

      if (hexData.captured_by) {
        flagContainer.addChild(
          newGraphic(
            getFlagCapturedIndicator(hexData.captured_by == gameState.player),
          ),
        );
      }

      const flagSprite = newSprite(textureMap["flag"]);
      flagSprite.anchor = 0.5;

      flagContainer.addChild(flagSprite);
      hexContainer.addChild(flagContainer);
    }

    if (
      (ccToKey(hexData.cc) in actionSpace &&
        actionSpace[ccToKey(hexData.cc)].highlighted) ||
      (state.highlightedCCs &&
        state.highlightedCCs.includes(ccToKey(hexData.cc)))
    ) {
      let highlight = newGraphic(highlightShape);
      hexContainer.addChild(highlight);
    }
    if (actionSpace[ccToKey(hexData.cc)]?.blueprintGhost) {
      const unitGhostSprite = newSprite(
        getTexture("unit", actionSpace[ccToKey(hexData.cc)].blueprintGhost),
      );
      unitGhostSprite.anchor = 0.5;
      hexContainer.addChild(unitGhostSprite);
    }

    actionTriggerZones.push([hexActionTriggerZones, realHexPosition]);
  }

  for (const hexData of gameState.map.hexes) {
    let realHexPosition = addRCs(ccToRC(hexData.cc), center);

    const filteredHexStatuses = [];

    for (let status of hexData.statuses) {
      if (
        !hexData.visible &&
        status.duration !== null &&
        hexData.last_visible_round !== null
      ) {
        if (gameState.round - hexData.last_visible_round >= status.duration) {
          continue;
        }
        status = {
          ...status,
          duration:
            status.duration - (gameState.round - hexData.last_visible_round),
        };
      }
      filteredHexStatuses.push(status);
    }

    const smallerSize = hexSize - 30;
    const [smallerWidth, smallerHeight] = getHexDimensions(smallerSize);

    const firstPoint = { x: 0, y: -smallerHeight / 2 };
    const lastPoint = { x: smallerWidth / 2, y: -smallerSize / 2 };

    const hexStatusesContainer = new Container();
    hexStatusesContainer.position = realHexPosition;
    map.addChild(hexStatusesContainer);

    addStatuses(
      ccToKey(hexData.cc) in hexStatusChanges
        ? hexStatusChanges[ccToKey(hexData.cc)].from
        : null,
      hexData.statuses,
      hexStatusesContainer,
      (idx, count) =>
        addRCs(
          firstPoint,
          constMultRC(
            asUnitVector(subRCs(lastPoint, firstPoint)),
            count <= 4 ? idx * 43 : (hexSize / count) * idx,
          ),
        ),
    );
  }

  for (const hexData of gameState.map.hexes) {
    if (hexData.unit) {
      const unitContainer = new Container();
      const baseUnitContainer = new Container();
      unitContainer.addChild(baseUnitContainer);
      const unitSprite = newSprite(getTexture("unit", hexData.unit.blueprint));
      unitSprite.anchor = 0.5;
      const size = (hexData.unit.size + 1) * 0.1 + 1;
      const targetScale = {
        x: hexData.unit.controller == gameState.players[0].name ? -size : size,

        y: size,
      };
      baseUnitContainer.scale = targetScale;

      const borderColor =
        hexData.unit.controller != gameState.player
          ? colors.enemy
          : colors.ally;
      const unitBorder = newGraphic(
        getUnitBackgroundGraphicsContext(borderColor),
      );

      baseUnitContainer.addChild(unitBorder);
      baseUnitContainer.addChild(unitSprite);

      const diamondCount = hexData.unit.size + 1;

      for (let i = 0; i < diamondCount; i++) {
        let sizeDiamond = newGraphic(
          getSizeDiamondGraphicsContext(borderColor),
        );

        sizeDiamond.y = -(unitHeight + borderWith) / 2;
        sizeDiamond.x =
          (diamondCount - 1) *
          (sizeIndicatorDiamondSize * 0.7) *
          (diamondCount > 1 ? (i * 2) / (diamondCount - 1) - 1 : 1);

        baseUnitContainer.addChild(sizeDiamond);
      }

      if (
        gameState.active_unit_context &&
        gameState.active_unit_context.unit.id == hexData.unit.id
      ) {
        const movementPoints = newText({
          text: `${gameState.active_unit_context.movement_points}`,
          style: largeTextStyle,
        });
        movementPoints.anchor = 0.5;
        unitContainer.addChild(movementPoints);
      }

      if (hexData.unit.exhausted) {
        unitContainer.angle = 90;
      }

      if (hexData.unit.id in unitRotations) {
        animations.push(
          makeAnimation(
            (c) =>
              (unitContainer.angle = hexData.unit.exhausted
                ? c * 90
                : (1 - c) * 90),
            200,
            sigmoid,
          ),
        );
      }

      addStatuses(
        hexData.unit.id in statusChanges
          ? statusChanges[hexData.unit.id].from
          : null,
        hexData.unit.statuses,
        unitContainer,
        (idx, count) => ({
          x: -unitSprite.width / 2,
          y:
            -unitSprite.height / 2 +
            (hexData.unit.statuses.length <= 4
              ? idx * 43
              : (150 / count) * idx),
        }),
      );

      const makeIndicatorDisplay = (
        currentValue: number,
        maxValue: number,
        fromColor: [number, number, number],
        toColor: [number, number, number],
      ): Container => {
        const container = new Container();
        const width = currentValue > 9 || maxValue > 9 ? 70 : 50;
        const height = 30;

        const bg = newGraphic(
          getIndicatorBg(
            currentValue,
            maxValue,
            width,
            height,
            fromColor,
            toColor,
          ),
        );

        container.addChild(bg);

        const primaryText = newText({
          text: `${currentValue}/${maxValue}`,
          style: primaryHealthIndicatorTextStyle,
        });
        primaryText.anchor = 0.5;
        container.addChild(primaryText);

        container.position = {
          x: unitSprite.width / 2 - 20,
          y: unitSprite.height / 2 - 10,
        };
        return container;
      };

      const healthIndicatorContainer = makeIndicatorDisplay(
        hexData.unit.max_health - hexData.unit.damage,
        hexData.unit.max_health,
        colors.fullHealth,
        colors.noHealth,
      );

      const sizeScale = (hexData.unit.size + 1) * 0.1 + 1;
      const imgWidth = unitSprite.width * sizeScale;
      const imgHeight = unitSprite.height * sizeScale;

      healthIndicatorContainer.position = {
        x: imgWidth / 2 - healthIndicatorContainer.width / 2 + 20,
        y: imgHeight / 2 - 10,
      };
      unitContainer.addChild(healthIndicatorContainer);

      if (hexData.unit.energy > 0 || hexData.unit.max_energy > 0) {
        const energyIndicatorContainer = makeIndicatorDisplay(
          hexData.unit.energy,
          hexData.unit.max_energy,
          colors.fullEnergy,
          colors.noEnergy,
        );
        energyIndicatorContainer.position = {
          x: imgWidth / 2 - energyIndicatorContainer.width / 2 + 20,
          y: imgHeight / 2 - 45,
        };
        unitContainer.addChild(energyIndicatorContainer);
      }

      if (hexData.unit.armor != 0) {
        const shieldContainer = new Container();
        const shieldSprite = newSprite(
          textureMap[
            hexData.unit.armor > 0 ? "shield_icon" : "shield_broken_icon"
          ],
        );
        shieldSprite.anchor = 0.5;
        const shieldText = newText({
          text: `${hexData.unit.armor}`,
          style: secondaryHealthIndicatorTextStyle,
        });
        shieldText.y = -2;
        shieldText.anchor = 0.5;
        shieldContainer.position = {
          x: -healthIndicatorContainer.width / 2 - 5,
          y: -healthIndicatorContainer.height / 2 + 9,
        };
        shieldContainer.addChild(shieldSprite);
        shieldContainer.addChild(shieldText);
        healthIndicatorContainer.addChild(shieldContainer);
      }

      if (unitDamages[hexData.unit.id]) {
        const damageContainer = new Container();
        const damageContentContainer = new Container();
        damageContainer.addChild(damageContentContainer);
        unitContainer.addChild(damageContainer);

        if (hexData.unit.exhausted) {
          damageContainer.angle = -90;
        }

        const damagedSprite = newSprite(
          getTexture(
            "icon",
            unitDamages[hexData.unit.id] > 0 ? "damaged" : "healed",
          ),
        );
        damagedSprite.anchor = 0.5;
        damageContentContainer.addChild(damagedSprite);
        const damageText = newText({
          text: `${Math.abs(unitDamages[hexData.unit.id])}`,
          style: damageStyle,
        });
        damageText.anchor = 0.5;
        damageContentContainer.addChild(damageText);
        animations.push(
          makeAnimation(
            (cursor) => (damageContentContainer.scale = cursor),
            200,
            sigmoid,
          ),
        );
        animations.push(
          makeAnimation(
            (cursor) => (damageContentContainer.rotation = cursor * 0.2),
            1000,
            shake,
            () => {
              unitContainer.removeChild(damageContainer);
            },
          ),
        );
      }

      const targetPosition = addRCs(ccToRC(hexData.cc), center);

      if (hexData.unit.is_ghost) {
        const unitSprite = newSprite(
          app.renderer.generateTexture(unitContainer),
        );
        unitSprite.position = targetPosition;
        const targetAlpha =
          (hexData.visible ? 0.5 : 0.6) -
          Math.min(
            hexData.last_visible_round === null
              ? 0
              : (gameState.round - hexData.last_visible_round) * 0.15,
            0.4,
          );
        unitSprite.alpha = targetAlpha;
        unitSprite.anchor = 0.5;
        map.addChild(unitSprite);
        if (hexData.unit.id in unitMoves) {
          animations.push(
            makeAnimation(
              (cursor) => {
                unitSprite.rotation = cursor * 0.2;
              },
              200,
              shake,
            ),
          );
        }
      } else {
        unitContainer.position = targetPosition;

        if (hexData.unit.id in unitMoves && !unitMoves[hexData.unit.id].from) {
          animations.push(
            makeAnimation(
              (cursor) => {
                baseUnitContainer.rotation = cursor * 0.2;
              },
              200,
              shake,
            ),
          );
        }

        if (hexData.unit.id in unitMoves && unitMoves[hexData.unit.id].from) {
          const previousPosition = addRCs(
            ccToRC(unitMoves[hexData.unit.id].from as CC),
            center,
          );
          animations.push(
            makeAnimation(
              (cursor) => {
                unitContainer.position = addRCs(
                  constMultRC(previousPosition, 1 - cursor),
                  constMultRC(targetPosition, cursor),
                );
              },
              200,
              sigmoid,
            ),
          );
        }

        map.addChild(unitContainer);
      }
    }
  }

  for (const [hexActionTriggerZones, rc] of actionTriggerZones) {
    for (const zone of hexActionTriggerZones) {
      zone.position = rc;
      map.addChild(zone);
    }
  }

  gameState.map.hexes.forEach((hexData) => {
    const menuItems = actionSpace[ccToKey(hexData.cc)]?.sideMenuItems || [];

    if (menuItems.length) {
      const hexContainer = new Container();
      map.addChild(hexContainer);
      hexContainer.position = addRCs(ccToRC(hexData.cc), center);
      const buttonHeight = 50;
      const totalSpaceNeeded = (buttonHeight + 20) * (menuItems.length - 1);

      for (const [idx, menuItem] of menuItems.entries()) {
        const itemsContainer = new Container();
        hexContainer.addChild(itemsContainer);
        const itemText = newText({
          text: `${menuItem.description}`,
          style: menuStyle,
        });
        // TODO
        const box = new Graphics()
          .roundRect(0, 0, itemText.width + buttonHeight + 5, buttonHeight, 5)
          .fill("0x666666");

        box.x = hexWidth / 2 + 10;
        box.y =
          (totalSpaceNeeded * idx) / Math.max(menuItems.length - 1, 1) -
          totalSpaceNeeded / 2 -
          buttonHeight / 2;

        const selectionSprite = newSprite(
          textureMap[selectionIconMap[menuItem.type]],
        );
        selectionSprite.scale = 0.15;
        selectionSprite.position = { x: box.x + 5, y: box.y + 5 };

        itemText.position = { x: box.x + buttonHeight, y: box.y };

        itemsContainer.addChild(box);
        itemsContainer.addChild(selectionSprite);
        itemsContainer.addChild(itemText);

        itemsContainer.eventMode = "static";
        itemsContainer.on("pointerdown", (event) => {
          if (event.button == 0) {
            menuItem.do({ x: 0, y: 0 });
          }
        });
      }
    }
  });

  map.eventMode = "static";
  map.on("globalpointermove", (event) => {
    // TODO ultra lmao, should just not render game beneath the sidebars instead...
    if (event.x < 400 || event.x > maxX - 400) {
      return;
    }
    const positionOnMap = subRCs(map.toLocal(event.global), center);
    const cc = rcToCC(positionOnMap);
    const hexData = gameState.map.hexes.find((h) => ccEquals(h.cc, cc));

    if (hexData) {
      const localPosition = subRCs(positionOnMap, ccToRC(cc));
      let detail: HoveredDetails = { type: "hex", hex: hexData };
      let hoverType = "hex";

      if (
        hexData.statuses.length &&
        rcInBox(
          localPosition,
          -22,
          -hexHeight / 2,
          hexWidth / 2 + 22,
          (hexHeight - hexSize) / 2,
        )
      ) {
        detail = { type: "statuses", statuses: hexData.statuses };
        hoverType = "hex-statuses";
      }

      if (hexData.unit) {
        if (
          hexData.unit.statuses.length && hexData.unit.exhausted
            ? rcInBox(localPosition, -74, -60 - 22, 148 + 22, 44)
            : rcInBox(localPosition, -60 - 22, -74 - 22, 44, 148 + 22)
        ) {
          detail = { type: "statuses", statuses: hexData.unit.statuses };
          hoverType = "unit-statuses";
        } else if (
          hexData.unit.exhausted
            ? rcInBox(localPosition, -74, -60, 148, 120)
            : rcInBox(localPosition, -60, -74, 120, 148)
        ) {
          detail = { type: "unit", unit: hexData.unit };
          hoverType = "unit";
        }
      } else if (actionSpace[ccToKey(hexData.cc)]?.blueprintGhost) {
        detail = {
          type: "blueprint",
          blueprint: actionSpace[ccToKey(hexData.cc)].blueprintGhost,
        };
      }

      const hoverTrigger = actionSpace[ccToKey(hexData.cc)]?.hoverTrigger;
      if (hoverTrigger) {
        hoverTrigger(localPosition);
      }

      const newKey = ccToKey(cc) + hoverType;
      const oldKey = previouslyHovered;
      previouslyHovered = newKey;
      if (newKey == oldKey) {
        return;
      }

      store.dispatch(hoverDetail(detail));
    }
  });

  return { map, graphics: createdObjects, animations };
};
