import {
  Cone,
  ConsecutiveAdjacentHexes,
  Decision,
  GameState,
  Hex,
  HexHexes,
  HexRing,
  NOfHexes,
  NOfUnits,
  RadiatingLine,
  Tree,
  TriHex,
  UnitOption,
} from "../../interfaces/gameState.ts";
import { ccFromKey, ccToKey } from "../geometry.ts";
import { Action, ActionSpace } from "./interface.ts";
import { activateMenu, store } from "../state/store.ts";

export const getUnitsOfHexes = (gameState: GameState): { [key: string]: Hex } =>
  Object.fromEntries(
    gameState.map.hexes
      .filter((h) => h.unit && h.visible)
      .map((h) => [h.unit.id, h]),
  );

export const getBaseActions = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  // TODO
  decision: Decision | null,
): { [key: string]: Action[] } => {
  const unitHexes: { [key: string]: Hex } = getUnitsOfHexes(gameState);

  const actions: { [key: string]: Action[] } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [ccToKey(hex.cc), []]),
  );

  if (decision && decision["type"] == "SelectOptionDecisionPoint") {
    for (const [idx, option] of decision.payload.options.entries()) {
      if (option.targetProfile.type == "OneOfUnits") {
        for (const [
          targetIdx,
          unit,
        ] of option.targetProfile.values.units.entries()) {
          actions[ccToKey(unitHexes[unit["id"]].cc)].push({
            type: option.values?.facet?.category || "generic",
            description: option.values?.facet?.name || "select unit",
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
            sourceOption: option,
            description:
              option.type == "MoveOption"
                ? "move"
                : option.values?.facet?.name || "select hex",
            do: () =>
              takeAction({
                index: idx,
                target: {
                  index: targetIdx,
                },
              }),
          });
        }
      } else if (option.targetProfile.type == "NOfHexes") {
        for (const [hexIdx, hex] of option.targetProfile.values.hexes.entries()) {
          actions[ccToKey(hex.cc)].push({
            type: "activated_ability",
            description:
              option.values?.facet?.name ||
              (option.targetProfile as NOfHexes).values.labels[0],
            do: () =>
              store.dispatch(
                activateMenu({
                  type: "NOfHexes",
                  selectedIndexes: [hexIdx],
                  targetProfile: option.targetProfile as NOfHexes,
                  optionIndex: idx,
                }),
              ),
          });
        }
      } else if (option.targetProfile.type == "NOfUnits") {
        for (const unit of option.targetProfile.values.units) {
          actions[ccToKey(unitHexes[unit.id].cc)].push({
            type: "activated_ability",
            description:
              option.values?.facet?.name ||
              (option.targetProfile as NOfUnits).values.labels[0],
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
      } else if (option.targetProfile.type == "Tree") {
        for (const [
          targetIdx,
          [treeOption, child],
        ] of option.targetProfile.values.rootNode.options.entries()) {
          actions[
            ccToKey(
              treeOption.type == "unit"
                ? unitHexes[treeOption.id].cc
                : treeOption.cc,
            )
          ].push({
            type: "activated_ability",
            description:
              option.values?.facet?.name ||
              option.targetProfile.values.rootNode.label,
            do: () =>
              store.dispatch(
                activateMenu({
                  type: "Tree",
                  optionIndex: idx,
                  targetProfile: option.targetProfile as Tree,
                  selectedIndexes: [targetIdx],
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
          description: option.values?.facet?.name || "select hexes",
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
          description: option.values?.facet?.name || "select hexes",
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
        option.targetProfile.type == "TriHex" &&
        gameState.activeUnitContext
      ) {
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "TriHex",
                optionIndex: idx,
                targetProfile: option.targetProfile as TriHex,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.targetProfile.type == "HexRing" &&
        gameState.activeUnitContext
      ) {
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "HexRing",
                optionIndex: idx,
                targetProfile: option.targetProfile as HexRing,
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
          description: option.values?.facet?.name || "select hexes",
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
        option.targetProfile.type == "Cone" &&
        gameState.activeUnitContext
      ) {
        actions[
          ccToKey(unitHexes[gameState.activeUnitContext.unit.id].cc)
        ].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "Cone",
                optionIndex: idx,
                targetProfile: option.targetProfile as Cone,
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
          description: option.values?.facet?.name || "activate ability",
          do: () => takeAction({ index: idx, target: null }),
        });
      }
    }
  }
  return actions;
};

export const getBaseActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  decision: Decision | null,
): ActionSpace => {
  const actions = getBaseActions(gameState, takeAction, decision);

  const previewMap: { [key: string]: UnitOption[] } = {};

  if (decision && decision.type == "SelectOptionDecisionPoint") {
    const activationOption = decision.payload.options.find(
      (option) => option.type == "ActivateUnitOption",
    );
    if (
      activationOption &&
      activationOption.targetProfile.type == "OneOfUnits"
    ) {
      const unitHexes: { [key: string]: Hex } = getUnitsOfHexes(gameState);
      for (const unit of activationOption.targetProfile.values.units) {
        previewMap[ccToKey(unitHexes[unit["id"]].cc)] =
          activationOption.values.actionsPreview[unit["id"]];
      }
    }
  }

  return {
    hexActions: Object.fromEntries(
      Object.entries(actions).map(([cc, _actions]) => [
        cc,
        _actions.length > 2 ||
        (_actions.length == 2 && _actions.some((a) => a.type == "menu")) ||
        new Set(_actions.map((a) => a.type)).size != _actions.length
          ? {
              actions: [
                ..._actions.filter(
                  (action) =>
                    action.sourceOption &&
                    action.sourceOption.type == "MoveOption",
                ),
                {
                  type: "menu",
                  description: "open menu",
                  do: () => {
                    store.dispatch(
                      activateMenu({
                        type: "ListMenu",
                        cc: ccFromKey(cc),
                      }),
                    );
                  },
                },
              ],
            }
          : {
              actions: _actions,
              highlighted: false,
              previewOptions: previewMap[cc],
            },
      ]),
    ),
    buttonAction: null,
  };
};
