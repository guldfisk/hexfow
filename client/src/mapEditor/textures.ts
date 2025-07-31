import { Assets, Texture } from "pixi.js";

import { GameObjectDetails } from "./interfaces/gameObjectDetails.ts";
import { receivedGameObjectDetails, store } from "./state/store.ts";
import { getImageUrl } from "../game/images.ts";

// TODO don't export?
export const textureMap: { [key: string]: Texture } = {};

export const loadGameTextures = async () => {
  // for (const uiIdentifier of [
  //   "hex_selection",
  //   "hex_selection_melee",
  //   "hex_selection_menu",
  //   "hex_selection_ranged_attack",
  //   "hex_selection_ability",
  //   "hex_selection_aoe",
  // ]) {
  //   textureMap[uiIdentifier] = await Assets.load(
  //     `/src/images/ui/${uiIdentifier}.png`,
  //   );
  // }
  for (const iconIdentifier of [
    // "shield_icon",
    // "shield_broken_icon",
    "flag_icon",
    // "closed_eye_icon",
  ]) {
    textureMap[iconIdentifier] = await Assets.load(
      `/src/images/icons/${iconIdentifier}.png`,
    );
  }

  await fetch(
    `${window.location.protocol + "//" + window.location.hostname}:8000/game-object-details`,
  ).then(async (response) => {
    let jsonResponse: GameObjectDetails = await response.json();

    for (const unitDetails of Object.values(jsonResponse.units)) {
      textureMap[unitDetails.identifier] = await Assets.load(
        getImageUrl("unit", unitDetails.identifier),
      );
    }

    for (const terrainDetails of Object.values(jsonResponse.terrain)) {
      textureMap[terrainDetails.identifier] = await Assets.load(
        getImageUrl("terrain", terrainDetails.identifier),
      );
    }

    for (const statusDetails of Object.values(jsonResponse.statuses)) {
      textureMap[statusDetails.identifier] = await Assets.load(
        getImageUrl("status", statusDetails.identifier),
      );
    }

    store.dispatch(receivedGameObjectDetails(jsonResponse));
  });
};
