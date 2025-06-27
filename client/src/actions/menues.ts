import { GameState, Hex } from "../interfaces/gameState.ts";
import { getBaseActions, getUnitsOfHexes } from "./actionSpace.ts";
import {
  ActionSpace,
  ConsecutiveAdjacentHexesMenu,
  HexHexesMenu,
  ListMenu,
  MenuData,
  NOfUnitsMenu,
  RadiatingLineMenu,
} from "./interface.ts";
import {
  addCCs,
  ccDistance,
  ccEquals,
  ccToKey,
  constMultCC,
  getNeighborsOffCC,
  subCCs,
} from "../geometry.ts";
import { advanceMenu, store } from "../state/store.ts";
import { mod, range } from "../utils/range.ts";

// TODO some common logic in this mess

const getNOfUnitsActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: NOfUnitsMenu,
): ActionSpace => {
  const unitHexes: { [key: string]: Hex } = getUnitsOfHexes(gameState);
  const actionSpace: ActionSpace = Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      { actions: [], highlighted: false },
    ]),
  );

  for (const unit of menu.targetProfile.values.units) {
    if (!menu.selectedUnits.includes(unit.id)) {
      actionSpace[ccToKey(unitHexes[unit.id].cc)].actions.push({
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
      actionSpace[ccToKey(unitHexes[unit.id].cc)].highlighted = true;
    }
  }
  return actionSpace;
};

const getNOfUnitsDescription = (
  gameState: GameState,
  menu: NOfUnitsMenu,
): string => {
  return menu.targetProfile.values.labels[menu.selectedUnits.length];
};

const getConsecutiveAdjacentHexesActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: ConsecutiveAdjacentHexesMenu,
): ActionSpace => {
  const actionSpace: ActionSpace = Object.fromEntries(
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
  const highlighted =
    menu.hovering !== null
      ? range(
          -menu.targetProfile.values.armLength,
          menu.targetProfile.values.armLength + 1,
        ).map((v) => mod(v + menu.hovering, options.length))
      : [];

  for (const [idx, option] of options.entries()) {
    actionSpace[ccToKey(option)] = {
      actions: [
        {
          type: "aoe",
          description: "select hexes",
          do: () => {
            // store.dispatch(deactivateMenu());
            takeAction({ index: menu.optionIndex, target: { cc: option } });
          },
        },
      ],
      highlighted: highlighted.includes(idx),
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: idx }));
      },
    };
  }
  return actionSpace;
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
  const actionSpace: ActionSpace = Object.fromEntries(
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
    actionSpace[ccToKey(cc)] = {
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
      highlighted: actionSpace[ccToKey(cc)].highlighted,
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: cc }));
      },
    };
  }
  return actionSpace;
};

const getHexHexesDescription = (
  gameState: GameState,
  menu: HexHexesMenu,
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

  const actionSpace: ActionSpace = Object.fromEntries(
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
    actionSpace[ccToKey(cc)] = {
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
      highlighted: actionSpace[ccToKey(cc)].highlighted,
      hoverTrigger: () => {
        store.dispatch(advanceMenu({ ...menu, hovering: cc }));
      },
    };
  }
  return actionSpace;
};

const getRadiatingLineDescription = (
  gameState: GameState,
  menu: RadiatingLineMenu,
): string => {
  return "select aoe";
};

const getListMenuActionSpace = (
  gameState: GameState,
  takeAction: (body: { [key: string]: any }) => void,
  menu: ListMenu,
): ActionSpace => {
  const actions = getBaseActions(gameState, takeAction);
  return Object.fromEntries(
    gameState.map.hexes.map((hex) => [
      ccToKey(hex.cc),
      {
        actions: [],
        sideMenuItems: ccEquals(hex.cc, menu.cc)
          ? actions[ccToKey(hex.cc)]
          : [],
      },
    ]),
  );
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
  NOfUnits: getNOfUnitsActionSpace,
  ConsecutiveAdjacentHexes: getConsecutiveAdjacentHexesActionSpace,
  HexHexes: getHexHexesActionSpace,
  RadiatingLine: getRadiatingLineActionSpace,
  ListMenu: getListMenuActionSpace,
};

export const menuDescribers: {
  [key: string]: (gameState: GameState, menu: MenuData) => string;
} = {
  NOfUnits: getNOfUnitsDescription,
  ConsecutiveAdjacentHexes: getConsecutiveAdjacentHexesDescription,
  HexHexes: getHexHexesDescription,
  RadiatingLine: getRadiatingLineDescription,
  ListMenu: getListMenuDescription,
};
