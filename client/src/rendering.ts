import {
  Application,
  Container,
  Graphics,
  GraphicsContext,
  Sprite,
  Text,
  TextStyle,
} from "pixi.js";
import { GameState, Hex } from "./interfaces/gameState.ts";
import type { FillInput } from "pixi.js/lib/scene/graphics/shared/FillTypes";

import { GameObjectDetails } from "./interfaces/gameObjectDetails.ts";
import {
  addRCs,
  assUnitVector,
  CCToRC,
  constMultRC,
  getHexDimensions,
  hexDistance,
  hexHeight,
  hexSize,
  hexVerticeOffsets,
  hexWidth,
  subRCs,
} from "./geometry.ts";
import { CC } from "./interfaces/geometry.ts";
import { textureMap } from "./textures.ts";
import { range } from "./utils/range.ts";

// TODO where?
const sizeMap: { S: number; M: number; L: number } = { S: 0.8, M: 1, L: 1.2 };

export const renderMap = (
  app: Application,
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  gameConnection: WebSocket,
): Container => {
  // TODO this shouldn't be here
  let maxX = window.innerWidth;
  let maxY = window.innerHeight;
  let center = { x: maxX / 2, y: maxY / 2 };

  // TODO make this shit react or something
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
      .setStrokeStyle({ color: "grey", pixelLine: true })
      .moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath().fill(color).stroke();
    return hexShape;
  };
  const getHexMask = (): GraphicsContext => {
    let hexShape = new GraphicsContext().moveTo(...hexVerticeOffsets[0]);
    hexVerticeOffsets.slice(1).forEach((vert) => hexShape.lineTo(...vert));
    hexShape.closePath();
    hexShape.fill({ alpha: 0 });
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
  const hexMaskShape = getHexMask();

  const dividerFrames = [
    [hexMaskShape],
    [0, 1].map(getDividerFrame),
    [1, 0, 2].map(getThreePartDividerFrame),
  ];

  const statusFrame = new GraphicsContext().circle(0, 0, 20).fill();
  const statusBorder = new GraphicsContext()
    .circle(0, 0, 20)
    .stroke({ color: "grey", pixelLine: true });

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
  const primaryHealthIndicatorTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 26,
    fill: "white",
    stroke: "black",
    strokeThickness: 2,
    // miterLimit: 2,
    // lineJoin: 'round',
    // strokeMiterLimit: 2,
    // strokeLineJoin: 'round',
    align: "center",
  });
  const secondaryHealthIndicatorTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 22,
    fill: "white",
    stroke: "black",
    strokeThickness: 2,
    // miterLimit: 2,
    // lineJoin: 'round',
    // strokeMiterLimit: 2,
    // strokeLineJoin: 'round',
    align: "center",
  });
  const energyTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 20,
    fill: 0x2163f3,
    align: "center",
  });
  const largeTextStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 80,
    fill: "blue",
    align: "center",
    stroke: "white",
  });
  const statusCountStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 25,
    fill: "white",
    align: "center",
    stroke: "black",
    strokeThickness: 3,
  });
  const ghostStyle = new TextStyle({
    fontFamily: "Arial",
    fontSize: 20,
    fill: "0x444444",
    align: "center",
  });

  const map = new Container();

  app.stage.addChild(map);

  const ccToKey = (cc: CC): string => `${cc.r},${cc.h}`;

  const unitHexes: { [key: string]: Hex } = Object.fromEntries(
    gameState.map.hexes
      .filter((h) => h.unit && h.visible)
      .map((h) => [h.unit.id, h]),
  );

  type Action = { type: string; content: { [key: string]: any } };
  const hexActionMap: { [key: string]: Action[] } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [ccToKey(hex.cc), []]),
  );

  const effortTypeMap: { [key: string]: string } = {
    RangedAttack: "hex_selection_ranged_attack",
    MeleeAttack: "hex_selection_melee",
    ActivatedAbility: "hex_selection_ability",
  };

  // TODO move this somewhere else
  if (
    gameState.decision &&
    gameState.decision["type"] == "SelectOptionDecisionPoint"
  ) {
    for (const [idx, option] of gameState.decision["payload"][
      "options"
    ].entries()) {
      if (option["targetProfile"]["type"] == "OneOfUnits") {
        for (const [targetIdx, unit] of option["targetProfile"]["values"][
          "units"
        ].entries()) {
          hexActionMap[ccToKey(unitHexes[unit["id"]].cc)].push({
            type:
              option.values?.facet?.type in effortTypeMap
                ? effortTypeMap[option.values?.facet?.type]
                : "hex_selection",
            content: {
              index: idx,
              target: {
                index: targetIdx,
              },
            },
          });
        }
      } else if (option["targetProfile"]["type"] == "OneOfHexes") {
        for (const [targetIdx, cc] of option["targetProfile"]["values"][
          "options"
        ].entries()) {
          hexActionMap[ccToKey(cc)].push({
            type:
              option.values?.facet?.type in effortTypeMap
                ? effortTypeMap[option.values?.facet?.type]
                : "hex_selection",
            content: {
              index: idx,
              target: {
                index: targetIdx,
              },
            },
          });
        }
      } else if (
        option["targetProfile"]["type"] == "ConsecutiveAdjacentHexes"
      ) {
      } else if (
        option["type"] == "EffortOption" &&
        option["targetProfile"]["type"] == "NoTarget" &&
        gameState.activeUnitContext
      ) {
        hexActionMap[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "hex_selection_ability",
          content: { index: idx, target: null },
        });
      }
    }
  }

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

    for (const [idx, action] of hexActionMap[ccToKey(hexData.cc)].entries()) {
      const selectionSprite = new Sprite(textureMap[action.type]);
      selectionSprite.anchor = 0.5;
      selectionSprite.alpha = 0.75;
      hexContainer.addChild(selectionSprite);
      let mask = new Graphics(
        dividerFrames[hexActionMap[ccToKey(hexData.cc)].length - 1][idx],
      );
      hexContainer.addChild(mask);
      selectionSprite.mask = mask;

      let triggerZone = new Graphics(
        dividerFrames[hexActionMap[ccToKey(hexData.cc)].length - 1][idx],
      );

      triggerZone.eventMode = "static";
      triggerZone.on("pointerdown", (event) => {
        console.log("click", event.button, hexData.cc);
        if (event.button == 0) {
          gameConnection.send(JSON.stringify(action.content));
        }
      });
      actionTriggerZones.push(triggerZone);
    }

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
        const statusContainer = new Container();
        const statusSprite = new Sprite(textureMap[status.type]);

        statusSprite.anchor = 0.5;
        statusContainer.addChild(statusSprite);

        const mask = new Graphics(statusFrame);
        statusContainer.addChild(mask);
        // mask.position = {x: -25 , y: -25 }
        statusSprite.mask = mask;

        statusContainer.position = {
          x: -unitSprite.width / 2,
          y:
            -unitSprite.height / 2 +
            (hexData.unit.statuses.length <= 4
              ? idx * 43
              : (150 / hexData.unit.statuses.length) * idx),
        };

        const border = new Graphics(statusBorder);
        statusContainer.addChild(border);

        const durationText = new Text({
          // text: `${status.duration}/${status.originalDuration}`,
          text: status.duration || status.stacks,
          style: statusCountStyle,
        });
        durationText.x = 17;
        durationText.y = -7;
        durationText.anchor = 0.5;
        statusContainer.addChild(durationText);

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
      // flagSprite.anchor = {x: 0, y: .5}
      // flagSprite.y = - hexHeight / 2 + 50
      flagSprite.x = -hexWidth / 2 + 10;
      flagSprite.y = -hexSize / 2;
      hexContainer.addChild(flagSprite);
    }

    for (const [idx, status] of hexData.statuses.entries()) {
      // TODO common status drawing logic
      const statusContainer = new Container();
      const statusSprite = new Sprite(textureMap[status.type]);

      statusSprite.anchor = 0.5;
      statusContainer.addChild(statusSprite);

      const mask = new Graphics(statusFrame);
      statusContainer.addChild(mask);
      statusSprite.mask = mask;

      const smallerSize = hexSize - 30;
      const [smallerWidth, smallerHeight] = getHexDimensions(smallerSize);

      const firstPoint = { x: 0, y: -smallerHeight / 2 };
      const lastPoint = { x: smallerWidth / 2, y: -smallerSize / 2 };

      statusContainer.position = addRCs(
        firstPoint,
        constMultRC(
          assUnitVector(subRCs(lastPoint, firstPoint)),
          hexData.statuses.length <= 4
            ? idx * 43
            : (hexSize / hexData.statuses.length) * idx,
        ),
      );

      const border = new Graphics(statusBorder);
      statusContainer.addChild(border);

      if (status.duration || status.stacks) {
        const durationText = new Text({
          text:
            !status.duration != !status.stacks
              ? `${status.duration || status.stacks}`
              : //   TODO how show this trash??
                `${status.stacks}-${status.duration}`,
          style: statusCountStyle,
        });
        durationText.x = 17;
        durationText.y = -7;
        durationText.anchor = 0.5;
        statusContainer.addChild(durationText);
      }

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

    for (const zone of actionTriggerZones) {
      hexContainer.addChild(zone);
    }
  });

  return map;
};
