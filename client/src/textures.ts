import { Assets, Texture } from "pixi.js";
import { recursiveCamelCase } from "./utils/case.ts";

import { GameObjectDetails } from "./interfaces/gameObjectDetails.ts";
import { receivedGameObjectDetails, store } from "./state/store.ts";

// TODO don't export?
export const textureMap: { [key: string]: Texture } = {};

export const loadGameTextures = async () => {
  for (const uiIdentifier of [
    "hex_selection",
    "hex_selection_melee",
    "hex_selection_menu",
    "hex_selection_ranged_attack",
    "hex_selection_ability",
  ]) {
    textureMap[uiIdentifier] = await Assets.load(
      `/src/images/ui/${uiIdentifier}.png`,
    );
  }
  for (const iconIdentifier of [
    "shield_icon",
    "shield_broken_icon",
    "flag_icon",
    "closed_eye_icon",
  ]) {
    textureMap[iconIdentifier] = await Assets.load(
      `/src/images/icons/${iconIdentifier}.png`,
    );
  }

  fetch("http://localhost:8000/game-object-details").then(async (response) => {
    let jsonResponse: GameObjectDetails = recursiveCamelCase(
      await response.json(),
    );

    for (const unitDetails of Object.values(jsonResponse.units)) {
      textureMap[unitDetails.identifier] = await Assets.load(
        unitDetails.smallImage,
      );
    }

    for (const terrainDetails of Object.values(jsonResponse.terrain)) {
      textureMap[terrainDetails.identifier] = await Assets.load(
        terrainDetails.image,
      );
    }

    for (const statusDetails of Object.values(jsonResponse.statuses)) {
      textureMap[statusDetails.identifier] = await Assets.load(
        statusDetails.image,
      );
    }

    store.dispatch(receivedGameObjectDetails(jsonResponse));
  });
};
