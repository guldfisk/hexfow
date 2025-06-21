import {
  ConsecutiveAdjacentHexes,
  GameState,
  Hex,
  HexHexes,
  NOfUnits,
  RadiatingLine,
} from "../interfaces/gameState.ts";
import { ccToKey } from "../geometry.ts";
import { Action, ActionSpace } from "./interface.ts";
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

  const actions: { [key: string]: Action[] } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [ccToKey(hex.cc), []]),
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
          actions[ccToKey(unitHexes[unit["id"]].cc)].push({
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
          actions[ccToKey(cc)].push({
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
          actions[ccToKey(unitHexes[unit.id].cc)].push({
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
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
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
        option.targetProfile.type == "HexHexes" &&
        gameState.activeUnitContext
      ) {
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "menu",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "HexHexes",
                optionIndex: idx,
                targetProfile: option.targetProfile as HexHexes,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.targetProfile.type == "RadiatingLine" &&
        gameState.activeUnitContext
      ) {
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "menu",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "RadiatingLine",
                optionIndex: idx,
                targetProfile: option.targetProfile as RadiatingLine,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.type == "EffortOption" &&
        option.targetProfile.type == "NoTarget" &&
        gameState.activeUnitContext
      ) {
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "activated_ability",
          do: () => takeAction({ index: idx, target: null }),
        });
      }
    }
  }
  return Object.fromEntries(
    Object.entries(actions).map(([cc, _actions]) => [
      cc,
      { actions: _actions, highlighted: false },
    ]),
  );
};
