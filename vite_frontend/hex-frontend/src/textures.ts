import { Assets, Texture } from "pixi.js";
import { recursiveCamelCase } from "./utils/case.ts";

// TODO yikes this shit's back.
// TODO also, get some structure on image folders / formats in general.
// import hexSelectionUrl from "./images/ui/hex_selection.png";
// import hexSelectionRangedAttackUrl from "./images/ui/hex_selection_ranged_attack.png";
// import hexSelectionMeleeAttackUrl from "./images/ui/hex_selection_melee.png";
// import hexSelectionAbilityUrl from "./images/ui/hex_selection_ability.png";

import { GameObjectDetails } from "./interfaces/gameObjectDetails.ts";
import { applicationState } from "./applicationState.ts";

// TODO don't export?
export const textureMap: { [key: string]: Texture } = {};

// export const getTexture = (identifier: string): Texture =>
//   textureMap[identifier];

export const loadGameTextures = async () => {
  // textureMap["selection"] = await Assets.load(hexSelectionUrl);
  // textureMap["selection_ranged"] = await Assets.load(
  //   hexSelectionRangedAttackUrl,
  // );
  // textureMap["selection_melee"] = await Assets.load(hexSelectionMeleeAttackUrl);
  // textureMap["selection_ability"] = await Assets.load(hexSelectionAbilityUrl);

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

    applicationState.gameObjectDetails = jsonResponse;
  });
};
