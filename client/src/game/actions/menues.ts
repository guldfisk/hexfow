import { GameState, Hex, TreeNode } from "../../interfaces/gameState.ts";
import { getBaseActions, getUnitsOfHexes } from "./actionSpace.ts";
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

// TODO some common logic in this mess

const getArrangeArmiesActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
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
          !(menu.swappingPosition && ccEquals(hex.cc, menu.swappingPosition)) &&
          menu.decisionPoint.payload.deploymentZone.some((v) =>
            ccEquals(v, hex.cc),
          ) &&
          !menu.submitted
            ? [
                {
                  type: "generic",
                  description: "swap",
                  do: () => {
                    if (menu.swappingPosition) {
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

  return {
    hexActions,
    buttonAction: menu.submitted
      ? null
      : {
          description: "submit",
          do: () => {
            takeAction({ deployments: Object.entries(menu.unitPositions) });
            store.dispatch(advanceMenu({ ...menu, submitted: true }));
          },
        },
  };
};

const getArrangeArmiesDescription = (
  gameState: GameState,
  menu: ArrangeArmyMenu,
): string => {
  return menu.submitted
    ? "waiting for opponent to submit their army"
    : "arrange army";
};

const getNOfHexesActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
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
          if (selectedIndexes.length >= menu.targetProfile.values.selectCount) {
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
      menu.targetProfile.values.minCount !== null &&
      menu.selectedIndexes.length >= menu.targetProfile.values.minCount
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
  menu: NOfHexesMenu,
): string => {
  return menu.targetProfile.values.labels[menu.selectedIndexes.length];
};

const getNOfUnitsActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: NOfUnitsMenu,
): ActionSpace => {
  const unitHexes: { [key: string]: Hex } = getUnitsOfHexes(gameState);
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
          if (selectedUnitIds.length >= menu.targetProfile.values.selectCount) {
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
      menu.targetProfile.values.minCount !== null &&
      menu.selectedUnits.length >= menu.targetProfile.values.minCount
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
  menu: NOfUnitsMenu,
): string => {
  return menu.targetProfile.values.labels[menu.selectedUnits.length];
};

const getTreeActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: TreeMenu,
): ActionSpace => {
  const unitHexes: { [key: string]: Hex } = getUnitsOfHexes(gameState);
  const hexActions: { [key: string]: HexActions } = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      { actions: [], highlighted: false },
    ]),
  );

  let currentNode = menu.targetProfile.values.rootNode;
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

const getTreeDescription = (gameState: GameState, menu: TreeMenu): string => {
  let currentNode = menu.targetProfile.values.rootNode;
  for (const idx of menu.selectedIndexes) {
    const [treeOption, child] = currentNode.options[idx];
    currentNode = child as TreeNode;
  }
  return currentNode.label;
};

const getConsecutiveAdjacentHexesActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
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
  const options = getNeighborsOffCC(menu.targetProfile.values.adjacentTo);
  const highlighted = menu.hovering
    ? hexArc(
        1,
        menu.targetProfile.values.armLength,
        menu.hovering,
        menu.targetProfile.values.adjacentTo,
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
  menu: ConsecutiveAdjacentHexesMenu,
): string => {
  return "select aoe";
};

const getHexHexesActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
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
  takeAction: (body: { [key: string]: any }) => void,
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
  menu: HexHexesMenu,
): string => {
  return "select aoe";
};

const getHexRingActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
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
  menu: HexRingMenu,
): string => {
  return "select aoe";
};

const getRadiatingLineActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: RadiatingLineMenu,
): ActionSpace => {
  const highlightedCCs = menu.hovering
    ? range(menu.targetProfile.values.length).map((i) =>
        ccToKey(
          addCCs(
            menu.hovering,
            constMultCC(
              subCCs(menu.hovering, menu.targetProfile.values.fromHex),
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

  for (const [targetIdx, cc] of menu.targetProfile.values.toHexes.entries()) {
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
  menu: RadiatingLineMenu,
): string => {
  return "select aoe";
};

const getConeActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: ConeMenu,
): ActionSpace => {
  let highlightedCCs: CC[] = [];
  if (menu.hovering) {
    const difference = subCCs(menu.hovering, menu.targetProfile.values.fromHex);
    for (const [
      idx,
      armLength,
    ] of menu.targetProfile.values.armLengths.entries()) {
      highlightedCCs = highlightedCCs.concat(
        hexArc(
          idx + 1,
          armLength,
          addCCs(menu.hovering, constMultCC(difference, idx)),
          menu.targetProfile.values.fromHex,
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

  for (const [targetIdx, cc] of menu.targetProfile.values.toHexes.entries()) {
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

const getConeDescription = (gameState: GameState, menu: ConeMenu): string => {
  return "select aoe";
};

const getListMenuActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: ListMenu,
): ActionSpace => {
  const actions = getBaseActions(gameState, takeAction, gameState.decision);
  return {
    hexActions: Object.fromEntries(
      gameState.map.hexes.map((hex) => [
        ccToKey(hex.cc),
        {
          actions: [],
          sideMenuItems: ccEquals(hex.cc, menu.cc)
            ? actions[ccToKey(hex.cc)]
            : [],
        },
      ]),
    ),
    buttonAction: null,
  };
};

const getListMenuDescription = (
  gameState: GameState,
  menu: ListMenu,
): string => {
  return "select item";
};

export const menuActionSpacers: {
  [key: string]: (
    gameState: GameState,
    takeAction: (body: { [key: string]: any }) => void,
    menu: MenuData,
  ) => ActionSpace;
} = {
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
  [key: string]: (gameState: GameState, menu: MenuData) => string;
} = {
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
