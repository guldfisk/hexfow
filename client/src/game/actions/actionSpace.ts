import {
  ActiveUnitContext,
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
  Unit,
} from "../../interfaces/gameState.ts";
import { ccFromKey, ccToKey } from "../geometry.ts";
import {
  Action,
  ActionSpace,
  DelayedActivation,
  TakeAction,
} from "./interface.ts";
import { activateMenu, setDelayedActivation, store } from "../state/store.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";
import { loadArmy } from "./load.ts";

export const getUnitIdHexMap = (gameState: GameState): { [key: string]: Hex } =>
  Object.fromEntries(
    gameState.map.hexes
      .filter((h) => h.unit && h.visible)
      .map((h) => [h.unit.id, h]),
  );
export const getUnitIdMap = (
  gameState: GameState,
): { [key: string]: { unit: Unit; hex: Hex } } =>
  Object.fromEntries(
    gameState.map.hexes
      .filter((h) => h.unit && h.visible)
      .map((h) => [h.unit.id, { unit: h.unit, hex: h }]),
  );

export const getBaseActions = (
  gameState: GameState,
  takeAction: TakeAction,
  // TODO
  decision: Decision | null,
  activeUnitContext: ActiveUnitContext | null,
  delayedActivation: DelayedActivation | null,
): { [key: string]: Action[] } => {
  if (delayedActivation) {
    decision = {
      type: "SelectOptionDecisionPoint",
      explanation: "preview",
      payload: { options: delayedActivation.options },
    };
    activeUnitContext = {
      unit: delayedActivation.unit,
      movement_points: 1,
    };
  }

  const unitHexes: { [key: string]: Hex } = getUnitIdHexMap(gameState);

  const actions: { [key: string]: Action[] } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [ccToKey(hex.cc), []]),
  );

  if (decision && decision["type"] == "SelectOptionDecisionPoint") {
    for (const [idx, option] of decision.payload.options.entries()) {
      if (option.target_profile.type == "OneOfUnits") {
        for (const [
          targetIdx,
          unit,
        ] of option.target_profile.values.units.entries()) {
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
      } else if (option.target_profile.type == "OneOfHexes") {
        for (const [
          targetIdx,
          cc,
        ] of option.target_profile.values.options.entries()) {
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
      } else if (option.target_profile.type == "NOfHexes") {
        for (const [
          hexIdx,
          hex,
        ] of option.target_profile.values.hexes.entries()) {
          actions[ccToKey(hex.cc)].push({
            type: "activated_ability",
            description:
              option.values?.facet?.name ||
              (option.target_profile as NOfHexes).values.labels[0],
            do: () =>
              store.dispatch(
                activateMenu({
                  type: "NOfHexes",
                  selectedIndexes: [hexIdx],
                  targetProfile: option.target_profile as NOfHexes,
                  optionIndex: idx,
                }),
              ),
          });
        }
      } else if (option.target_profile.type == "NOfUnits") {
        for (const unit of option.target_profile.values.units) {
          actions[ccToKey(unitHexes[unit.id].cc)].push({
            type: "activated_ability",
            description:
              option.values?.facet?.name ||
              (option.target_profile as NOfUnits).values.labels[0],
            do: () =>
              store.dispatch(
                activateMenu({
                  type: "NOfUnits",
                  selectedUnits: [unit.id],
                  targetProfile: option.target_profile as NOfUnits,
                  optionIndex: idx,
                }),
              ),
          });
        }
      } else if (option.target_profile.type == "Tree") {
        for (const [
          targetIdx,
          [treeOption, child],
        ] of option.target_profile.values.root_node.options.entries()) {
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
              option.target_profile.values.root_node.label,
            do: () =>
              store.dispatch(
                activateMenu({
                  type: "Tree",
                  optionIndex: idx,
                  targetProfile: option.target_profile as Tree,
                  selectedIndexes: [targetIdx],
                }),
              ),
          });
        }
      } else if (
        option.target_profile.type == "ConsecutiveAdjacentHexes" &&
        activeUnitContext
      ) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "ConsecutiveAdjacentHexes",
                optionIndex: idx,
                targetProfile:
                  option.target_profile as ConsecutiveAdjacentHexes,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.target_profile.type == "HexHexes" &&
        activeUnitContext
      ) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "HexHexes",
                optionIndex: idx,
                targetProfile: option.target_profile as HexHexes,
                hovering: null,
              }),
            ),
        });
      } else if (option.target_profile.type == "TriHex" && activeUnitContext) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "TriHex",
                optionIndex: idx,
                targetProfile: option.target_profile as TriHex,
                hovering: null,
              }),
            ),
        });
      } else if (option.target_profile.type == "HexRing" && activeUnitContext) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "HexRing",
                optionIndex: idx,
                targetProfile: option.target_profile as HexRing,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.target_profile.type == "RadiatingLine" &&
        activeUnitContext
      ) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "RadiatingLine",
                optionIndex: idx,
                targetProfile: option.target_profile as RadiatingLine,
                hovering: null,
              }),
            ),
        });
      } else if (option.target_profile.type == "Cone" && activeUnitContext) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "menu",
          description: option.values?.facet?.name || "select hexes",
          do: () =>
            store.dispatch(
              activateMenu({
                type: "Cone",
                optionIndex: idx,
                targetProfile: option.target_profile as Cone,
                hovering: null,
              }),
            ),
        });
      } else if (
        option.type == "EffortOption" &&
        option.target_profile.type == "NoTarget" &&
        activeUnitContext
      ) {
        actions[ccToKey(unitHexes[activeUnitContext.unit.id].cc)].push({
          type: "activated_ability",
          description: option.values?.facet?.name || "activate ability",
          do: () => takeAction({ index: idx, target: {} }),
        });
      }
    }
  }
  return actions;
};

export const getBaseActionSpace = (
  gameState: GameState,
  takeAction: TakeAction,
  gameObjectDetails: GameObjectDetails,
  decision: Decision | null,
  activeUnitContext: ActiveUnitContext | null,
  delayedActivation: DelayedActivation | null,
): ActionSpace => {
  if (decision && decision.type == "SelectOptionDecisionPoint") {
    const actions = getBaseActions(
      gameState,
      takeAction,
      decision,
      activeUnitContext,
      delayedActivation,
    );

    if (!delayedActivation) {
      for (const [idx, option] of decision.payload.options.entries()) {
        if (
          option.type == "ActivateUnitOption" &&
          option.target_profile.type == "OneOfUnits"
        ) {
          const unitIdMap = getUnitIdMap(gameState);
          for (const [
            targetIdx,
            unit,
          ] of option.target_profile.values.units.entries()) {
            actions[ccToKey(unitIdMap[unit.id].hex.cc)] = [
              {
                type: "generic",
                description: "activate unit",
                do: () =>
                  store.dispatch(
                    setDelayedActivation({
                      optionIndex: idx,
                      targetIndex: targetIdx,
                      unit: unitIdMap[unit.id].unit,
                      options: option.values.actions_preview[unit.id],
                    }),
                  ),
              },
            ];
          }
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
              },
        ]),
      ),
      buttonAction: null,
    };
  } else if (decision && decision["type"] == "SelectArmyDecisionPoint") {
    return {
      hexActions: Object.fromEntries(
        decision.payload.deployment_zone.map((cc) => [
          ccToKey(cc),
          {
            actions: [
              {
                type: "generic",
                description: "",
                do: () => null,
              },
            ],
          },
        ]),
      ),
      buttonAction: null,
      loadFileAction: {
        description: "load army list",
        do: (armyContent) => loadArmy(armyContent, decision, gameObjectDetails),
      },
    };
  } else if (decision && decision["type"] == "DeployArmyDecisionPoint") {
    return {
      hexActions: Object.fromEntries(
        decision.payload.deployment_zone.map((cc) => [
          ccToKey(cc),
          {
            actions: [
              {
                type: "generic",
                description: "",
                do: () => null,
              },
            ],
          },
        ]),
      ),
      buttonAction: {
        description: "deploy",
        do: () => {
          store.dispatch(
            activateMenu({
              type: "ArrangeArmy",
              decisionPoint: decision,
              units: decision.payload.units.map(
                (identifier) => gameObjectDetails.units[identifier],
              ),
              unitPositions: {},
              swappingPosition: null,
              submitted: false,
              uncloseable: true,
            }),
          );
        },
      },
      unitListActions: {
        units: decision.payload.units.map(
          (identifier) => gameObjectDetails.units[identifier],
        ),
        onClick: (unit) => {
          store.dispatch(
            activateMenu({
              type: "ArrangeArmy",
              decisionPoint: decision,
              units: decision.payload.units.map(
                (identifier) => gameObjectDetails.units[identifier],
              ),
              unitPositions: {
                [unit.identifier]: decision.payload.deployment_zone[0],
              },
              swappingPosition: null,
              submitted: false,
              uncloseable: true,
            }),
          );
        },
      },
    };
  } else if (decision && decision.type == "SelectOptionAtHexDecisionPoint") {
    return {
      hexActions: {
        [ccToKey(decision.payload.hex)]: {
          actions: [],
          sideMenuItems: decision.payload.options.map((entry, idx) => ({
            type: "generic",
            description: entry,
            do: () => takeAction({ index: idx }),
          })),
        },
      },
      buttonAction: null,
    };
  }
  return { hexActions: {}, buttonAction: null };
};
