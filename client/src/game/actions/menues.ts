import { GameState, Hex, TreeNode } from "../../interfaces/gameState.ts";
import { getBaseActions, getUnitIdHexMap } from "./actionSpace.ts";
import {
  ActionSpace,
  ArrangeArmyMenu,
  ConeMenu,
  ConsecutiveAdjacentHexesMenu,
  HexActions,
  HexHexesMenu,
  HexRingMenu,
  ListMenu,
  MenuData,
  NOfHexesMenu,
  NOfUnitsMenu,
  RadiatingLineMenu,
  SelectArmyMenu,
  TakeAction,
  TreeMenu,
  TriHexMenu,
} from "./interface.ts";
import {
  addCCs,
  ccDistance,
  ccEquals,
  ccToKey,
  constMultCC,
  cornerToKey,
  getCornerCCNeighbors,
  getNeighborsOffCC,
  hexArc,
  hexVerticeOffsetsRcs,
  rcDistance,
  subCCs,
} from "../geometry.ts";
import { advanceMenu, store } from "../state/store.ts";
import { range } from "../utils/range.ts";
import { CC, Corner, RC } from "../../interfaces/geometry.ts";
import { min } from "../utils/min.ts";
import { loadArmy } from "./load.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";

// TODO some common logic in this mess

const getSelectArmyActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: SelectArmyMenu,
): ActionSpace => {
  const points = menu.selectedUnits
    .map((unit) => unit.price || 0)
    .reduce((a, b) => a + b, 0);

  return menu.submitted
    ? { hexActions: {}, buttonAction: null }
    : {
        hexActions: Object.fromEntries(
          menu.decisionPoint.payload.deployment_zone.map((cc) => [
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
        loadFileAction: {
          description: "load army list",
          do: (armyContent) =>
            loadArmy(armyContent, menu.decisionPoint, gameObjectDetails),
        },
        buttonAction:
          points <=
            menu.decisionPoint.payload.deployment_spec.max_army_points &&
          menu.selectedUnits.length <=
            menu.decisionPoint.payload.deployment_spec.max_army_units
            ? {
                description: "submit",
                do: () => {
                  takeAction({
                    units: menu.selectedUnits.map((unit) => unit.identifier),
                  });
                  store.dispatch(advanceMenu({ ...menu, submitted: true }));
                },
              }
            : null,
        unitListActions: {
          units: menu.selectedUnits,
          onClick: null,
        },
      };
};

const getSelectArmyDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: SelectArmyMenu,
): string => {
  return menu.submitted
    ? "waiting for opponent to select their army"
    : `current army: ${menu.selectedUnits
        .map((unit) => unit.price || 0)
        .reduce((a, b) => a + b, 0)}/${
        menu.decisionPoint.payload.deployment_spec.max_army_points
      } points ${menu.selectedUnits.length}/${
        menu.decisionPoint.payload.deployment_spec.max_army_units
      } units`;
};

const getArrangeArmiesActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: ArrangeArmyMenu,
): ActionSpace => {
  const positionsMap: { [key: string]: string } = Object.fromEntries(
    Object.entries(menu.unitPositions).map(([name, cc]) => [ccToKey(cc), name]),
  );

  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions:
          !menu.submitted &&
          menu.decisionPoint.payload.deployment_zone.some((v) =>
            ccEquals(v, hex.cc),
          )
            ? [
                {
                  type: "generic",
                  description: "swap",
                  do: () => {
                    if (menu.swappingPosition) {
                      if (ccEquals(menu.swappingPosition, hex.cc)) {
                        store.dispatch(
                          advanceMenu({
                            ...menu,
                            unitPositions: Object.fromEntries(
                              Object.entries(menu.unitPositions).filter(
                                ([, cc]) => !ccEquals(cc, hex.cc),
                              ),
                            ),
                            swappingPosition: null,
                          }),
                        );
                      } else {
                        const newPositions = { ...menu.unitPositions };
                        if (positionsMap[ccToKey(menu.swappingPosition)]) {
                          newPositions[
                            positionsMap[ccToKey(menu.swappingPosition)]
                          ] = hex.cc;
                        }
                        if (positionsMap[ccToKey(hex.cc)]) {
                          newPositions[positionsMap[ccToKey(hex.cc)]] =
                            menu.swappingPosition;
                        }
                        store.dispatch(
                          advanceMenu({
                            ...menu,
                            unitPositions: newPositions,
                            swappingPosition: null,
                          }),
                        );
                      }
                    } else {
                      store.dispatch(
                        advanceMenu({ ...menu, swappingPosition: hex.cc }),
                      );
                    }
                  },
                },
              ]
            : [],
        highlighted:
          menu.swappingPosition && ccEquals(hex.cc, menu.swappingPosition),
        blueprintGhost: positionsMap[ccToKey(hex.cc)],
      },
    ]),
  );

  return menu.submitted
    ? { hexActions, buttonAction: null }
    : {
        hexActions,
        buttonAction:
          Object.keys(menu.unitPositions)
            .map((identifier) => gameObjectDetails.units[identifier].price || 0)
            .reduce((a, b) => a + b, 0) <=
            menu.decisionPoint.payload.deployment_spec.max_deployment_points &&
          Object.keys(menu.unitPositions).length <=
            menu.decisionPoint.payload.deployment_spec.max_deployment_units
            ? {
                description: "submit",
                do: () => {
                  takeAction({
                    deployments: Object.entries(menu.unitPositions),
                  });
                  store.dispatch(advanceMenu({ ...menu, submitted: true }));
                },
              }
            : null,
        unitListActions: {
          units: menu.units.filter(
            (unit) => !menu.unitPositions[unit.identifier],
          ),
          onClick: (unit) => {
            store.dispatch(
              advanceMenu({
                ...menu,
                unitPositions: {
                  ...menu.unitPositions,
                  [unit.identifier]:
                    menu.decisionPoint.payload.deployment_zone.find(
                      (cc) =>
                        !Object.values(menu.unitPositions).some((_cc) =>
                          ccEquals(cc, _cc),
                        ),
                    ),
                },
                swappingPosition: null,
              }),
            );
          },
        },
      };
};

const getArrangeArmiesDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: ArrangeArmyMenu,
): string => {
  return menu.submitted
    ? "waiting for opponent to select their army"
    : `current army: ${Object.keys(menu.unitPositions)
        .map((identifier) => gameObjectDetails.units[identifier].price || 0)
        .reduce((a, b) => a + b, 0)}/${
        menu.decisionPoint.payload.deployment_spec.max_deployment_points
      } points ${Object.keys(menu.unitPositions).length}/${
        menu.decisionPoint.payload.deployment_spec.max_deployment_units
      } units`;
};

const getNOfHexesActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: NOfHexesMenu,
): ActionSpace => {
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      { actions: [], highlighted: false },
    ]),
  );

  for (const [idx, hex] of menu.targetProfile.values.hexes.entries()) {
    if (!menu.selectedIndexes.includes(idx)) {
      hexActions[ccToKey(hex.cc)].actions.push({
        type: "activated_ability",
        description:
          menu.targetProfile.values.labels[menu.selectedIndexes.length],
        do: () => {
          const selectedIndexes = menu.selectedIndexes.concat([idx]);
          if (
            selectedIndexes.length >= menu.targetProfile.values.select_count
          ) {
            takeAction({
              index: menu.optionIndex,
              target: {
                indexes: selectedIndexes,
              },
            });
          } else {
            store.dispatch(advanceMenu({ ...menu, selectedIndexes }));
          }
        },
      });
    } else {
      hexActions[ccToKey(hex.cc)].highlighted = true;
    }
  }
  return {
    hexActions,
    buttonAction:
      menu.targetProfile.values.min_count !== null &&
      menu.selectedIndexes.length >= menu.targetProfile.values.min_count
        ? {
            description: "finish selection",
            do: () => {
              takeAction({
                index: menu.optionIndex,
                target: {
                  indexes: menu.selectedIndexes,
                },
              });
            },
          }
        : null,
  };
};

const getNOfHexesDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: NOfHexesMenu,
): string => {
  return menu.targetProfile.values.labels[menu.selectedIndexes.length];
};

const getNOfUnitsActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: NOfUnitsMenu,
): ActionSpace => {
  const unitHexes: { [key: string]: Hex } = getUnitIdHexMap(gameState);
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      { actions: [], highlighted: false },
    ]),
  );

  for (const unit of menu.targetProfile.values.units) {
    if (!menu.selectedUnits.includes(unit.id)) {
      hexActions[ccToKey(unitHexes[unit.id].cc)].actions.push({
        type: "activated_ability",
        description:
          menu.targetProfile.values.labels[menu.selectedUnits.length],
        do: () => {
          const selectedUnitIds = menu.selectedUnits.concat([unit.id]);
          if (
            selectedUnitIds.length >= menu.targetProfile.values.select_count
          ) {
            takeAction({
              index: menu.optionIndex,
              target: {
                indexes: selectedUnitIds.map((id) =>
                  menu.targetProfile.values.units.findIndex(
                    (unit) => unit.id == id,
                  ),
                ),
              },
            });
          } else {
            store.dispatch(
              advanceMenu({ ...menu, selectedUnits: selectedUnitIds }),
            );
          }
        },
      });
    } else {
      hexActions[ccToKey(unitHexes[unit.id].cc)].highlighted = true;
    }
  }
  return {
    hexActions,
    buttonAction:
      menu.targetProfile.values.min_count !== null &&
      menu.selectedUnits.length >= menu.targetProfile.values.min_count
        ? {
            description: "finish selection",
            do: () => {
              takeAction({
                index: menu.optionIndex,
                target: {
                  indexes: menu.selectedUnits.map((id) =>
                    menu.targetProfile.values.units.findIndex(
                      (unit) => unit.id == id,
                    ),
                  ),
                },
              });
            },
          }
        : null,
  };
};

const getNOfUnitsDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: NOfUnitsMenu,
): string => {
  return menu.targetProfile.values.labels[menu.selectedUnits.length];
};

const getTreeActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: TreeMenu,
): ActionSpace => {
  const unitHexes: { [key: string]: Hex } = getUnitIdHexMap(gameState);
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      { actions: [], highlighted: false },
    ]),
  );

  let currentNode = menu.targetProfile.values.root_node;
  for (const idx of menu.selectedIndexes) {
    const [treeOption, child] = currentNode.options[idx];
    hexActions[
      ccToKey(
        treeOption.type == "unit" ? unitHexes[treeOption.id].cc : treeOption.cc,
      )
    ].highlighted = true;
    currentNode = child as TreeNode;
  }

  for (const [
    targetIdx,
    [treeOption, child],
  ] of currentNode.options.entries()) {
    hexActions[
      ccToKey(
        treeOption.type == "unit" ? unitHexes[treeOption.id].cc : treeOption.cc,
      )
    ].actions.push({
      type: "activated_ability",
      description: currentNode.label,
      do: () => {
        if (child) {
          store.dispatch(
            advanceMenu({
              ...menu,
              selectedIndexes: menu.selectedIndexes.concat(targetIdx),
            }),
          );
        } else {
          takeAction({
            index: menu.optionIndex,
            target: { indexes: menu.selectedIndexes.concat(targetIdx) },
          });
        }
      },
    });
  }
  return { hexActions, buttonAction: null };
};

const getTreeDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: TreeMenu,
): string => {
  let currentNode = menu.targetProfile.values.root_node;
  for (const idx of menu.selectedIndexes) {
    const [treeOption, child] = currentNode.options[idx];
    currentNode = child as TreeNode;
  }
  return currentNode.label;
};

const getConsecutiveAdjacentHexesActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: ConsecutiveAdjacentHexesMenu,
): ActionSpace => {
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions: [],
        highlighted: false,
        hoverTrigger: () =>
          store.dispatch(advanceMenu({ ...menu, hovering: null })),
      },
    ]),
  );
  const options = getNeighborsOffCC(menu.targetProfile.values.adjacent_to);
  const highlighted = menu.hovering
    ? hexArc(
        1,
        menu.targetProfile.values.arm_length,
        menu.hovering,
        menu.targetProfile.values.adjacent_to,
      ).map(ccToKey)
    : [];

  for (const option of options) {
    hexActions[ccToKey(option)] = {
      actions: [
        {
          type: "aoe",
          description: "select hexes",
          do: () => {
            takeAction({ index: menu.optionIndex, target: { cc: option } });
          },
        },
      ],
      highlighted: highlighted.includes(ccToKey(option)),
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: option }));
      },
    };
  }
  return { hexActions, buttonAction: null };
};

const getConsecutiveAdjacentHexesDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: ConsecutiveAdjacentHexesMenu,
): string => {
  return "select aoe";
};

const getHexHexesActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: HexHexesMenu,
): ActionSpace => {
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions: [],
        highlighted:
          menu.hovering &&
          ccDistance(menu.hovering, hex.cc) <= menu.targetProfile.values.radius,
      },
    ]),
  );

  for (const [targetIdx, cc] of menu.targetProfile.values.centers.entries()) {
    hexActions[ccToKey(cc)] = {
      actions: [
        {
          type: "aoe",
          description: "select hexes",
          do: () => {
            takeAction({
              index: menu.optionIndex,
              target: {
                index: targetIdx,
              },
            });
          },
        },
      ],
      highlighted: hexActions[ccToKey(cc)].highlighted,
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: cc }));
      },
    };
  }
  return { hexActions, buttonAction: null };
};

const getHexHexesDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: HexHexesMenu,
): string => {
  return "select aoe";
};

interface CornerOption {
  cornerIdx: number;
  direction: number;
  corner: Corner;
}

const getTriHexActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: TriHexMenu,
): ActionSpace => {
  const cornerOptions: { [key: string]: CornerOption[] } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [ccToKey(hex.cc), []]),
  );

  for (const [
    cornerIdx,
    corner,
  ] of menu.targetProfile.values.corners.entries()) {
    for (const [cc, direction] of getCornerCCNeighbors(corner)) {
      cornerOptions[ccToKey(cc)].push({ cornerIdx, direction, corner });
    }
  }

  const hoveredKey = menu.hovering ? cornerToKey(menu.hovering) : null;

  return {
    hexActions: Object.fromEntries(
      Object.entries(cornerOptions).map(
        ([ccKey, cornerOptions]): [string, HexActions] => {
          if (!cornerOptions.length) {
            return [ccKey, { actions: [] }];
          }
          const getClosestOption = (locationPosition: RC) =>
            min(cornerOptions, (option) =>
              rcDistance(
                hexVerticeOffsetsRcs[option.direction],
                locationPosition,
              ),
            );
          return [
            ccKey,
            {
              actions: [
                {
                  type: "aoe",
                  description: "select hexes",
                  do: (localPosition) =>
                    takeAction({
                      index: menu.optionIndex,
                      target: {
                        index: getClosestOption(localPosition).cornerIdx,
                      },
                    }),
                },
              ],
              highlighted: cornerOptions.some(
                (option) => cornerToKey(option.corner) == hoveredKey,
              ),
              hoverTrigger: (localPosition) => {
                store.dispatch(
                  advanceMenu({
                    ...menu,
                    hovering: getClosestOption(localPosition).corner,
                  }),
                );
              },
            },
          ];
        },
      ),
    ),
    buttonAction: null,
  };
};

const getTriHexDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: HexHexesMenu,
): string => {
  return "select aoe";
};

const getHexRingActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: HexRingMenu,
): ActionSpace => {
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions: [],
        highlighted:
          !!menu.hovering &&
          ccDistance(menu.hovering, hex.cc) == menu.targetProfile.values.radius,
      },
    ]),
  );

  for (const [targetIdx, cc] of menu.targetProfile.values.centers.entries()) {
    hexActions[ccToKey(cc)] = {
      actions: [
        {
          type: "aoe",
          description: "select hexes",
          do: () => {
            takeAction({
              index: menu.optionIndex,
              target: {
                index: targetIdx,
              },
            });
          },
        },
      ],
      highlighted: hexActions[ccToKey(cc)].highlighted,
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: cc }));
      },
    };
  }
  return { hexActions, buttonAction: null };
};

const getHexRingDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: HexRingMenu,
): string => {
  return "select aoe";
};

const getRadiatingLineActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: RadiatingLineMenu,
): ActionSpace => {
  const highlightedCCs = menu.hovering
    ? range(menu.targetProfile.values.length).map((i) =>
        ccToKey(
          addCCs(
            menu.hovering,
            constMultCC(
              subCCs(menu.hovering, menu.targetProfile.values.from_hex),
              i,
            ),
          ),
        ),
      )
    : [];

  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions: [],
        highlighted: highlightedCCs.includes(ccToKey(hex.cc)),
        hoverTrigger: () => {
          store.dispatch(advanceMenu({ ...menu, hovering: null }));
        },
      },
    ]),
  );

  for (const [targetIdx, cc] of menu.targetProfile.values.to_hexes.entries()) {
    hexActions[ccToKey(cc)] = {
      actions: [
        {
          type: "aoe",
          description: "select hexes",
          do: () => {
            // store.dispatch(deactivateMenu());
            takeAction({
              index: menu.optionIndex,
              target: {
                index: targetIdx,
              },
            });
          },
        },
      ],
      highlighted: hexActions[ccToKey(cc)].highlighted,
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: cc }));
      },
    };
  }
  return { hexActions, buttonAction: null };
};

const getRadiatingLineDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: RadiatingLineMenu,
): string => {
  return "select aoe";
};

const getConeActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: ConeMenu,
): ActionSpace => {
  let highlightedCCs: CC[] = [];
  if (menu.hovering) {
    const difference = subCCs(
      menu.hovering,
      menu.targetProfile.values.from_hex,
    );
    for (const [
      idx,
      armLength,
    ] of menu.targetProfile.values.arm_lengths.entries()) {
      highlightedCCs = highlightedCCs.concat(
        hexArc(
          idx + 1,
          armLength,
          addCCs(menu.hovering, constMultCC(difference, idx)),
          menu.targetProfile.values.from_hex,
        ),
      );
    }
  }

  const highlightedCCKeys = highlightedCCs.map(ccToKey);

  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions: [],
        highlighted: highlightedCCKeys.includes(ccToKey(hex.cc)),
        hoverTrigger: () => {
          store.dispatch(advanceMenu({ ...menu, hovering: null }));
        },
      },
    ]),
  );

  for (const [targetIdx, cc] of menu.targetProfile.values.to_hexes.entries()) {
    hexActions[ccToKey(cc)] = {
      actions: [
        {
          type: "aoe",
          description: "select hexes",

          do: () => {
            takeAction({
              index: menu.optionIndex,
              target: {
                index: targetIdx,
              },
            });
          },
        },
      ],
      highlighted: hexActions[ccToKey(cc)].highlighted,
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: cc }));
      },
    };
  }
  return { hexActions, buttonAction: null };
};

const getConeDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: ConeMenu,
): string => {
  return "select aoe";
};

const getListMenuActionSpace = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  takeAction: TakeAction,
  menu: ListMenu,
): ActionSpace => {
  const actions = getBaseActions(
    gameState,
    takeAction,
    gameState.decision,
    gameState.active_unit_context,
    // TODO yikes
    store.getState().delayedActivation,
  );
  return {
    hexActions: Object.fromEntries(
      gameState.map.hexes.map((hex) => [
        ccToKey(hex.cc),
        {
          actions: [],
          sideMenuItems: ccEquals(hex.cc, menu.cc)
            ? actions[ccToKey(hex.cc)].filter(
                (action) =>
                  !(
                    action.sourceOption &&
                    action.sourceOption.type == "MoveOption"
                  ),
              )
            : [],
        },
      ]),
    ),
    buttonAction: null,
  };
};

const getListMenuDescription = (
  gameState: GameState,
  gameObjectDetails: GameObjectDetails,
  menu: ListMenu,
): string => {
  return "select item";
};

export const menuActionSpacers: {
  [key: string]: (
    gameState: GameState,
    gameObjectDetails: GameObjectDetails,
    takeAction: TakeAction,
    menu: MenuData,
  ) => ActionSpace;
} = {
  SelectArmy: getSelectArmyActionSpace,
  ArrangeArmy: getArrangeArmiesActionSpace,
  NOfUnits: getNOfUnitsActionSpace,
  NOfHexes: getNOfHexesActionSpace,
  ConsecutiveAdjacentHexes: getConsecutiveAdjacentHexesActionSpace,
  HexHexes: getHexHexesActionSpace,
  RadiatingLine: getRadiatingLineActionSpace,
  ListMenu: getListMenuActionSpace,
  HexRing: getHexRingActionSpace,
  Cone: getConeActionSpace,
  Tree: getTreeActionSpace,
  TriHex: getTriHexActionSpace,
};

export const menuDescribers: {
  [key: string]: (
    gameState: GameState,
    gameObjectDetails: GameObjectDetails,
    menu: MenuData,
  ) => string;
} = {
  SelectArmy: getSelectArmyDescription,
  ArrangeArmy: getArrangeArmiesDescription,
  NOfUnits: getNOfUnitsDescription,
  NOfHexes: getNOfHexesDescription,
  ConsecutiveAdjacentHexes: getConsecutiveAdjacentHexesDescription,
  HexHexes: getHexHexesDescription,
  RadiatingLine: getRadiatingLineDescription,
  ListMenu: getListMenuDescription,
  HexRing: getHexRingDescription,
  Cone: getConeDescription,
  Tree: getTreeDescription,
  TriHex: getTriHexDescription,
};
