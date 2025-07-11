import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Sprite,
  Text,
  TextStyle,
} from "pixi.js";
import { GameState, Intention, Status } from "./interfaces/gameState.ts";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";

import { GameObjectDetails } from "./interfaces/gameObjectDetails.ts";
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
  rcInBox,
  rcToCC,
  subRCs,
} from "./geometry.ts";
import { textureMap } from "./textures.ts";
import { range } from "./utils/range.ts";
import { deactivateMenu, hoverDetail, store } from "./state/store.ts";
import { getBaseActionSpace } from "./actions/actionSpace.ts";
import { MenuData, selectionIcon } from "./actions/interface.ts";
import { menuActionSpacers } from "./actions/menues.ts";
import { HoveredDetails } from "./interfaces/details.ts";

const sizeScales: { S: number; M: number; L: number } = {
  S: 0.9,
  M: 1,
  L: 1.1,
};
const sizeArrowPositions: { S: number; M: number; L: number } = {
  S: 1,
  M: 0,
  L: -1,
};

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
// const colors = {
//   enemy: "0x9b1711",
//   ally: "0x2f71e7",
//   // fullHealth: [128, 215, 100],
//   fullHealth: [88, 230, 68],
//   noHealth: [43, 1, 1],
//   // fullEnergy: [250, 218, 77],
//   fullEnergy: [223, 213, 45],
//   noEnergy: [133, 10, 7],
// };

export const renderMap = (
  app: Application,
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: MenuData | null,
  highlightedCCs: string[] | null,
  gameConnection: WebSocket,
): Container => {
  // TODO this shouldn't be here
  let maxX = window.innerWidth;
  let maxY = window.innerHeight;
  let center = { x: maxX / 2, y: maxY / 2 };

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
    range(3).map((i) =>
      hexShape.lineTo(...hexVerticeOffsets[(i + num * 2) % 6]),
    );
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
  const ghostStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 20,
    fill: "0x444444",
    align: "center",
  });
  const menuStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 40,
    fill: "black",
    align: "center",
  });

  const map = new Container();

  app.stage.addChild(map);

  const actionSpace = menu
    ? menuActionSpacers[menu.type](
        gameState,
        (body) => gameConnection.send(JSON.stringify(body)),
        menu,
      )
    : getBaseActionSpace(gameState, (body) =>
        gameConnection.send(JSON.stringify(body)),
      );

  for (const hexData of gameState.map.hexes) {
    let realHexPosition = addRCs(ccToRC(hexData.cc), center);

    const hexContainer = new Container();
    map.addChild(hexContainer);

    const terrainSprite = new Sprite(textureMap[hexData.terrain]);
    terrainSprite.anchor = 0.5;

    let hex = new Graphics(
      hexData.visible ? visibleHexShape : invisibleHexShape,
    );
    hexContainer.position = realHexPosition;

    let hexMask = new Graphics(hexMaskShape);

    hexContainer.addChild(hexMask);

    // TODO this works apparently, but is it the correct way to do it??
    hexContainer.mask = hexMask;
    hexContainer.addChild(terrainSprite);

    hexContainer.addChild(hex);

    const label = new Text({
      text: `${hexData.cc.r},${hexData.cc.h}`,
      style: smallTextStyle,
    });
    label.anchor = 0.5;
    label.y = hexSize / 2 + 25;
    hexContainer.addChild(label);

    const actionTriggerZones = [];

    for (const [idx, action] of actionSpace[
      ccToKey(hexData.cc)
    ].actions.entries()) {
      const selectionSprite = new Sprite(
        textureMap[selectionIconMap[action.type]],
      );
      selectionSprite.anchor = 0.5;
      selectionSprite.alpha = 0.75;
      hexContainer.addChild(selectionSprite);
      let mask = new Graphics(
        dividerFrames[actionSpace[ccToKey(hexData.cc)].actions.length - 1][idx],
      );
      hexContainer.addChild(mask);
      selectionSprite.mask = mask;

      let triggerZone = new Graphics(
        dividerFrames[actionSpace[ccToKey(hexData.cc)].actions.length - 1][idx],
      );
      triggerZone.eventMode = "static";
      triggerZone.on("pointerdown", (event) => {
        console.log("click", event.button, hexData.cc);
        if (event.button == 0) {
          action.do();
        }
      });
      actionTriggerZones.push(triggerZone);
    }

    // TODO common trigger zone
    if (menu && !actionSpace[ccToKey(hexData.cc)].actions.length) {
      let triggerZone = new Graphics(dividerFrames[0][0]);
      triggerZone.eventMode = "static";
      triggerZone.on("pointerdown", (event) => {
        console.log("click", event.button, hexData.cc);
        if (event.button == 0) {
          store.dispatch(deactivateMenu());
        }
      });
      actionTriggerZones.push(triggerZone);
    }

    const makeStatusIndicator = (
      status: Status,
      intention: Intention | null,
    ): Container => {
      const statusContainer = new Container();
      const statusSprite = new Sprite(textureMap[status.type]);

      if (intention) {
        const frame = new Graphics(intentionBorderMap[intention]);
        statusContainer.addChild(frame);
      }

      statusSprite.anchor = 0.5;
      statusContainer.addChild(statusSprite);

      const mask = new Graphics(!intention ? hexStatusFrame : statusFrame);
      statusContainer.addChild(mask);
      statusSprite.mask = mask;

      if (!intention) {
        const border = new Graphics(hexStatusBorder);
        statusContainer.addChild(border);
      }

      if (status.stacks) {
        const durationText = new Text({
          text: `${status.stacks}`,
          style: stacksStyle,
        });
        durationText.x = -17;
        durationText.y = -7;
        durationText.anchor = 0.5;
        statusContainer.addChild(durationText);
      }

      if (status.duration) {
        const durationText = new Text({
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

    if (hexData.unit) {
      const unitContainer = new Container();
      const baseUnitContainer = new Container();
      unitContainer.addChild(baseUnitContainer);
      const unitSprite = new Sprite(textureMap[hexData.unit.blueprint]);
      unitSprite.anchor = 0.5;
      baseUnitContainer.scale = sizeScales[hexData.unit.size];
      if (hexData.unit.controller != gameState.player) {
        baseUnitContainer.scale.x = -baseUnitContainer.scale.x;
      }

      const borderWith = 4;
      const arrowLength = 15;

      let graphics = new Graphics()
        .moveTo(
          -unitSprite.width / 2 - borderWith,
          -unitSprite.height / 2 - borderWith,
        )
        .lineTo(
          unitSprite.width / 2 + borderWith,
          -unitSprite.height / 2 - borderWith,
        )
        .lineTo(
          unitSprite.width / 2 + borderWith + arrowLength,
          (unitSprite.height / 2 + borderWith) *
            sizeArrowPositions[hexData.unit.size],
        )
        .lineTo(
          unitSprite.width / 2 + borderWith,
          unitSprite.height / 2 + borderWith,
        )
        .lineTo(
          -unitSprite.width / 2 - borderWith,
          unitSprite.height / 2 + borderWith,
        )
        .closePath()
        .fill(
          hexData.unit.controller != gameState.player
            ? colors.enemy
            : colors.ally,
        );

      baseUnitContainer.addChild(graphics);
      baseUnitContainer.addChild(unitSprite);

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

      if (hexData.unit.exhausted) {
        unitContainer.angle = 90;
      }

      for (const [idx, status] of hexData.unit.statuses.entries()) {
        const statusContainer = makeStatusIndicator(status, status.intention);
        statusContainer.position = {
          x: -unitSprite.width / 2,
          y:
            -unitSprite.height / 2 +
            (hexData.unit.statuses.length <= 4
              ? idx * 43
              : (150 / hexData.unit.statuses.length) * idx),
        };

        unitContainer.addChild(statusContainer);
      }

      const makeIndicatorDisplay = (
        currentValue: number,
        maxValue: number,
        fromColor: [number, number, number],
        toColor: [number, number, number],
      ): Container => {
        const container = new Container();
        const width = currentValue > 9 || maxValue > 9 ? 70 : 50;
        const height = 30;

        const ratio = currentValue / maxValue;

        const bg = new Graphics()
          .roundRect(-width / 2, -height / 2, width, height, 6)
          .fill(
            fromColor.map(
              (fv, i) => (fv * ratio + toColor[i] * (1 - ratio)) / 255,
            ),
          )
          .stroke({ color: "black", pixelLine: true });

        container.addChild(bg);

        const primaryText = new Text({
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
        hexData.unit.maxHealth - hexData.unit.damage,
        hexData.unit.maxHealth,
        colors.fullHealth,
        colors.noHealth,
      );

      const imgWidth = unitSprite.width * sizeScales[hexData.unit.size];
      const imgHeight = unitSprite.height * sizeScales[hexData.unit.size];

      healthIndicatorContainer.position = {
        x: imgWidth / 2 - healthIndicatorContainer.width / 2 + 20,
        y: imgHeight / 2 - 10,
      };
      unitContainer.addChild(healthIndicatorContainer);

      if (hexData.unit.energy > 0 || hexData.unit.maxEnergy > 0) {
        const energyIndicatorContainer = makeIndicatorDisplay(
          hexData.unit.energy,
          hexData.unit.maxEnergy,
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
        const shieldSprite = new Sprite(
          textureMap[
            hexData.unit.armor > 0 ? "shield_icon" : "shield_broken_icon"
          ],
        );
        shieldSprite.anchor = 0.5;
        const shieldText = new Text({
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

      if (hexData.unit.isGhost) {
        const unitSprite = new Sprite(
          app.renderer.generateTexture(unitContainer),
        );
        unitSprite.alpha = 0.5;
        unitSprite.anchor = 0.5;
        hexContainer.addChild(unitSprite);
      } else {
        hexContainer.addChild(unitContainer);
      }
    }

    if (hexData.isObjective) {
      const flagSprite = new Sprite(textureMap["flag_icon"]);
      flagSprite.x = -hexWidth / 2 + 10;
      flagSprite.y = -hexSize / 2;
      hexContainer.addChild(flagSprite);
    }

    for (const [idx, status] of hexData.statuses.entries()) {
      const statusContainer = makeStatusIndicator(status, null);

      const smallerSize = hexSize - 30;
      const [smallerWidth, smallerHeight] = getHexDimensions(smallerSize);

      const firstPoint = { x: 0, y: -smallerHeight / 2 };
      const lastPoint = { x: smallerWidth / 2, y: -smallerSize / 2 };

      statusContainer.position = addRCs(
        firstPoint,
        constMultRC(
          asUnitVector(subRCs(lastPoint, firstPoint)),
          hexData.statuses.length <= 4
            ? idx * 43
            : (hexSize / hexData.statuses.length) * idx,
        ),
      );

      hexContainer.addChild(statusContainer);
    }

    if (!hexData.visible) {
      const eyeContainer = new Container();
      const eyeIcon = new Sprite(textureMap["closed_eye_icon"]);
      eyeIcon.anchor = 0.5;

      if (
        hexData.lastVisibleRound !== null &&
        gameState.round - hexData.lastVisibleRound > 0
      ) {
        const eyeText = new Text({
          text: `${gameState.round - hexData.lastVisibleRound}`,
          style: ghostStyle,
        });
        eyeText.anchor = 0.5;
        eyeText.x = 40;
        eyeContainer.addChild(eyeText);
        eyeContainer.x = -10;
      }

      eyeContainer.addChild(eyeIcon);
      eyeContainer.y = hexHeight / 2 - 40;
      eyeContainer.x = -10;
      hexContainer.addChild(eyeContainer);
    }

    if (
      actionSpace[ccToKey(hexData.cc)].highlighted ||
      (highlightedCCs && highlightedCCs.includes(ccToKey(hexData.cc)))
    ) {
      let highlight = new Graphics(highlightShape);
      hexContainer.addChild(highlight);
    }

    for (const zone of actionTriggerZones) {
      hexContainer.addChild(zone);
    }
    hexContainer.eventMode = "static";
  }

  gameState.map.hexes.forEach((hexData) => {
    const menuItems = actionSpace[ccToKey(hexData.cc)].sideMenuItems || [];

    if (menuItems.length) {
      const hexContainer = new Container();
      map.addChild(hexContainer);
      hexContainer.position = addRCs(ccToRC(hexData.cc), center);
      const buttonHeight = 50;
      const totalSpaceNeeded = (buttonHeight + 20) * (menuItems.length - 1);

      for (const [idx, menuItem] of menuItems.entries()) {
        const itemsContainer = new Container();
        hexContainer.addChild(itemsContainer);
        const itemText = new Text({
          text: `${menuItem.description}`,
          style: menuStyle,
        });
        const box = new Graphics()
          .roundRect(0, 0, itemText.width + buttonHeight + 5, buttonHeight, 5)
          .fill("0x666666");

        box.x = hexWidth / 2 + 10;
        box.y =
          (totalSpaceNeeded * idx) / Math.max(menuItems.length - 1, 1) -
          totalSpaceNeeded / 2 -
          buttonHeight / 2;

        const selectionSprite = new Sprite(
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
            menuItem.do();
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

      if (
        hexData.statuses.length &&
        rcInBox(localPosition, -22, -hexHeight / 2, hexWidth / 2 + 22, (hexHeight - hexSize) / 2)
      ) {
        detail = {type: 'statuses', statuses: hexData.statuses}
      }

      if (hexData.unit) {
        if (
          hexData.unit.statuses.length && hexData.unit.exhausted
            ? rcInBox(localPosition, -74, -60 - 22, 148 + 22, 44)
            : rcInBox(localPosition, -60 - 22, -74 - 22, 44, 148 + 22)
        ) {
          detail = { type: "statuses", statuses: hexData.unit.statuses };
        } else if (
          hexData.unit.exhausted
            ? rcInBox(localPosition, -74, -60, 148, 120)
            : rcInBox(localPosition, -60, -74, 120, 148)
        ) {
          detail = { type: "unit", unit: hexData.unit };
        }
      }

      store.dispatch(hoverDetail(detail));

      const hoverTrigger = actionSpace[ccToKey(hexData.cc)].hoverTrigger;
      if (hoverTrigger) {
        hoverTrigger();
      }
    }
  });

  return map;
};
