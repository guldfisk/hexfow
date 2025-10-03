import { Assets, Texture } from "pixi.js";

import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";
import { getImageUrl, ResourceType } from "../image/images.ts";
import {
  loadedImage,
  receivedGameObjectDetails,
  store,
} from "./state/store.ts";

// TODO don't export?
export const textureMap: { [key: string]: Texture } = {};

export const unitFallback = "unit_fallback";
export const unitFallbackUrl = "/src/images/units/fallback.png";
export const statusFallback = "status_fallback";
export const statusFallbackUrl = "/src/images/statuses/fallback.png";

export const lazyLoadTexture = (identifier: string, url: string) =>
  Assets.load(url).then((texture) => {
    textureMap[identifier] = texture;
    store.dispatch(loadedImage());
  });

export const getTexture = (
  resourceType: ResourceType,
  resourceIdentifier: string,
): Texture => {
  if (resourceIdentifier in textureMap) {
    return textureMap[resourceIdentifier];
  }
  lazyLoadTexture(
    resourceIdentifier,
    getImageUrl(resourceType, resourceIdentifier),
  );
  if (resourceType == "unit") {
    return textureMap[unitFallback];
  }
  return textureMap[statusFallback];
};

const lazyLoad = (identifier: string, url: string) =>
  Assets.load(url).then((texture) => (textureMap[identifier] = texture));

export const backgroundLoadTextures = (
  gameObjectDetails: GameObjectDetails,
) => {
  for (const status of Object.values(gameObjectDetails.statuses)) {
    lazyLoad(status.identifier, getImageUrl("status", status.identifier));
  }
  for (const unit of Object.values(gameObjectDetails.units)) {
    lazyLoad(unit.identifier, getImageUrl("unit", unit.identifier));
  }
};

export const loadGameTextures = async () => {
  const promises: Promise<Texture>[] = [];
  const load = (identifier: string, url: string) =>
    promises.push(
      Assets.load(url).then((texture) => (textureMap[identifier] = texture)),
    );

  for (const uiIdentifier of [
    "hex_selection",
    "hex_selection_melee",
    "hex_selection_menu",
    "hex_selection_ranged_attack",
    "hex_selection_ability",
    "hex_selection_aoe",
  ]) {
    load(uiIdentifier, `/src/images/ui/${uiIdentifier}.png`);
  }
  for (const iconIdentifier of [
    "shield",
    "shield_broken",
    "flag",
    "closed_eye",
    "damaged",
    "healed",
  ]) {
    load(iconIdentifier, getImageUrl("icon", iconIdentifier));
  }

  load(unitFallback, unitFallbackUrl);
  load(statusFallback, statusFallbackUrl);

  return await fetch(
    `${window.location.protocol + "//" + window.location.hostname}:8000/game-object-details`,
  ).then(async (response) => {
    let jsonResponse: GameObjectDetails = await response.json();

    for (const terrainDetails of Object.values(jsonResponse.terrain)) {
      load(
        terrainDetails.identifier,
        getImageUrl("terrain", terrainDetails.identifier),
      );
    }

    await Promise.all(promises);
    store.dispatch(receivedGameObjectDetails(jsonResponse));
    return jsonResponse;
  });
};
