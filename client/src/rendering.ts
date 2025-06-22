import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Sprite,
  Text,
  TextStyle,
} from "pixi.js";
import { GameState, Status } from "./interfaces/gameState.ts";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";

import { GameObjectDetails } from "./interfaces/gameObjectDetails.ts";
import {
  addRCs,
  asUnitVector,
  ccToKey,
  ccToRC,
  constMultRC,
  getHexDimensions,
  getHexVerticeOffsets,
  hexDistance,
  hexHeight,
  hexSize,
  hexVerticeOffsets,
  hexWidth,
  subRCs,
} from "./geometry.ts";
import { textureMap } from "./textures.ts";
import { range } from "./utils/range.ts";
import { deactivateMenu, hoverUnit, store } from "./state/store.ts";
import { getBaseActionSpace } from "./actions/actionSpace.ts";
import { MenuData, selectionIcon } from "./actions/interface.ts";
import { menuActionSpacers } from "./actions/menues.ts";

// TODO where?
const sizeMap: { S: number; M: number; L: number } = { S: 0.8, M: 1, L: 1.2 };

const selectionIconMap: { [key in selectionIcon]: string } = {
  ranged_attack: "hex_selection_ranged_attack",
  melee_attack: "hex_selection_melee",
  activated_ability: "hex_selection_ability",
  generic: "hex_selection",
  aoe: "hex_selection_aoe",
  menu: "hex_selection_menu",
};

export const renderMap = (
  app: Application,
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: MenuData | null,
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

  const statusFrame = new GraphicsContext().circle(0, 0, 20).fill();
  const statusBorder = new GraphicsContext()
    .circle(0, 0, 20)
    .stroke({ color: "grey", pixelLine: true });

  const hexStatusFrame = getHexMask({alpha: 0}, 22);
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

  gameState.map.hexes.forEach((hexData) => {
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
      text: `${hexData.cc.r},${hexData.cc.h}\n${hexDistance({ r: 0, h: 0 }, hexData.cc)}`,
      style: smallTextStyle,
    });
    label.anchor = 0.5;
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
      hexOutline: boolean,
    ): Container => {
      const statusContainer = new Container();
      const statusSprite = new Sprite(textureMap[status.type]);

      statusSprite.anchor = 0.5;
      statusContainer.addChild(statusSprite);

      const mask = new Graphics(hexOutline ? hexStatusFrame : statusFrame);
      statusContainer.addChild(mask);
      statusSprite.mask = mask;

      const border = new Graphics(hexOutline ? hexStatusBorder : statusBorder);
      statusContainer.addChild(border);

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
      const unitSprite = new Sprite(textureMap[hexData.unit.blueprint]);
      unitSprite.anchor = 0.5;
      if (hexData.unit.controller != gameState.player) {
        unitSprite.scale.x = -unitSprite.scale.x;
      }

      unitContainer.addChild(unitSprite);

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
      unitContainer.addChild(graphics);

      if (hexData.unit.exhausted) {
        unitContainer.angle = 90;
      }

      for (const [idx, status] of hexData.unit.statuses.entries()) {
        const statusContainer = makeStatusIndicator(status, false);
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
        [237, 10, 10],
        [22, 3, 1],
      );

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

      healthIndicatorContainer.position = {
        x: unitSprite.width / 2 - healthIndicatorContainer.width / 2 + 20,
        y: unitSprite.height / 2 - 10,
      };
      unitContainer.addChild(healthIndicatorContainer);

      if (hexData.unit.energy > 0 || hexData.unit.maxEnergy > 0) {
        const energyIndicatorContainer = makeIndicatorDisplay(
          hexData.unit.energy,
          hexData.unit.maxEnergy,
          [47, 103, 248],
          [5, 17, 74],
        );
        energyIndicatorContainer.position = {
          x: unitSprite.width / 2 - energyIndicatorContainer.width / 2 + 20,
          y: unitSprite.height / 2 - 45,
        };
        unitContainer.addChild(energyIndicatorContainer);
      }

      // TODO scaling entire container is dumb
      unitContainer.scale = sizeMap[hexData.unit.size];

      hexContainer.addChild(unitContainer);
    }

    if (hexData.isObjective) {
      const flagSprite = new Sprite(textureMap["flag_icon"]);
      flagSprite.x = -hexWidth / 2 + 10;
      flagSprite.y = -hexSize / 2;
      hexContainer.addChild(flagSprite);
    }

    for (const [idx, status] of hexData.statuses.entries()) {
      const statusContainer = makeStatusIndicator(status, true);

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

    if (actionSpace[ccToKey(hexData.cc)].highlighted) {
      let highlight = new Graphics(highlightShape);
      hexContainer.addChild(highlight);
    }

    for (const zone of actionTriggerZones) {
      hexContainer.addChild(zone);
    }
    hexContainer.eventMode = "static";
    hexContainer.on("mouseenter", (event) => {
      if (hexData.unit) {
        store.dispatch(hoverUnit(hexData.unit));
      }
      const hoverTrigger = actionSpace[ccToKey(hexData.cc)].hoverTrigger;
      if (hoverTrigger) {
        hoverTrigger();
      }
    });
  });

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

  return map;
};
