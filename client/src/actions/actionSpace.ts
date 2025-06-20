import {
  ConsecutiveAdjacentHexes,
  GameState,
  Hex,
  NOfUnits,
} from "../interfaces/gameState.ts";
import { ccToKey } from "../geometry.ts";
import { ActionSpace } from "./interface.ts";
import { activateMenu, store } from "../state/store.ts";

export const getUnitsOfHexes = (gameState: GameState): { [key: string]: Hex } =>
  Object.fromEntries(
    gameState.map.hexes
      .filter((h) => h.unit && h.visible)
      .map((h) => [h.unit.id, h]),
  );

export const getBaseActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
): ActionSpace => {
  const unitHexes: { [key: string]: Hex } = getUnitsOfHexes(gameState);

  const actionSpace: ActionSpace = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      { actions: [], highlighted: false },
    ]),
  );

  if (
    gameState.decision &&
    gameState.decision["type"] == "SelectOptionDecisionPoint"
  ) {
    for (const [idx, option] of gameState.decision.payload.options.entries()) {
      if (option.targetProfile.type == "OneOfUnits") {
        for (const [
          targetIdx,
          unit,
        ] of option.targetProfile.values.units.entries()) {
          actionSpace[ccToKey(unitHexes[unit["id"]].cc)].actions.push({
            type: option.values?.facet?.category || "generic",
            do: () =>
              takeAction({
                index: idx,
                target: {
                  index: targetIdx,
                },
              }),
          });
        }
      } else if (option.targetProfile.type == "OneOfHexes") {
        for (const [
          targetIdx,
          cc,
        ] of option.targetProfile.values.options.entries()) {
          actionSpace[ccToKey(cc)].actions.push({
            type: option.values?.facet?.category || "generic",

            do: () =>
              takeAction({
                index: idx,
                target: {
                  index: targetIdx,
                },
              }),
          });
        }
      } else if (option.targetProfile.type == "NOfUnits") {
        for (const unit of option.targetProfile.values.units) {
          actionSpace[ccToKey(unitHexes[unit.id].cc)].actions.push({
            type: "activated_ability",
            do: () =>
              store.dispatch(
                activateMenu({
                  type: "NOfUnits",
                  selectedUnits: [unit.id],
                  targetProfile: option.targetProfile as NOfUnits,
                  optionIndex: idx,
                }),
              ),
          });
        }
      } else if (
        option.targetProfile.type == "ConsecutiveAdjacentHexes" &&
        gameState.activeUnitContext
      ) {
        actionSpace[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].actions.push({
          type: "menu",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "ConsecutiveAdjacentHexes",
                optionIndex: idx,
                targetProfile: option.targetProfile as ConsecutiveAdjacentHexes,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.type == "EffortOption" &&
        option.targetProfile.type == "NoTarget" &&
        gameState.activeUnitContext
      ) {
        actionSpace[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].actions.push({
          type: "activated_ability",
          do: () => takeAction({ index: idx, target: null }),
        });
      }
    }
  }
  return actionSpace;
};
