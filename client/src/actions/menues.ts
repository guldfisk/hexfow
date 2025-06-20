import { GameState, Hex } from "../interfaces/gameState.ts";
import { getUnitsOfHexes } from "./actionSpace.ts";
import {
  ActionSpace,
  ConsecutiveAdjacentHexesMenu,
  MenuData,
  NOfUnitsMenu,
} from "./interface.ts";
import { ccToKey, getNeighborsOffCC } from "../geometry.ts";
import { activateMenu, store } from "../state/store.ts";
import { mod, range } from "../utils/range.ts";

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
              activateMenu({ ...menu, selectedUnits: selectedUnitIds }),
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
      { actions: [], highlighted: false },
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
  console.log(highlighted);

  for (const [idx, option] of options.entries()) {
    actionSpace[ccToKey(option)] = {
      actions: [
        {
          type: "aoe",
          do: () =>
            takeAction({ index: menu.optionIndex, target: { cc: option } }),
        },
      ],
      highlighted: highlighted.includes(idx),
      hoverTrigger: () => {
        store.dispatch(activateMenu({ ...menu, hovering: idx }));
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

export const menuActionSpacers: {
  [key: string]: (
    gameState: GameState,
    takeAction: (body: { [key: string]: any }) => void,
    menu: MenuData,
  ) => ActionSpace;
} = {
  NOfUnits: getNOfUnitsActionSpace,
  ConsecutiveAdjacentHexes: getConsecutiveAdjacentHexesActionSpace,
};

export const menuDescribers: {
  [key: string]: (gameState: GameState, menu: MenuData) => string;
} = {
  NOfUnits: getNOfUnitsDescription,
  ConsecutiveAdjacentHexes: getConsecutiveAdjacentHexesDescription,
};
