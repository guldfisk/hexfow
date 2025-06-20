import { GameState, Hex } from "../interfaces/gameState.ts";
import { getUnitsOfHexes } from "./actionSpace.ts";
import { ActionSpace, MenuData, NOfUnitsMenu } from "./interface.ts";
import { ccToKey } from "../geometry.ts";
import { activateMenu, store } from "../state/store.ts";

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

export const menuActionSpacers: {
  [key: string]: (
    gameState: GameState,
    takeAction: (body: { [key: string]: any }) => void,
    menu: MenuData,
  ) => ActionSpace;
} = { NOfUnits: getNOfUnitsActionSpace };

export const menuDescribers: {
  [key: string]: (gameState: GameState, menu: MenuData) => string;
} = { NOfUnits: getNOfUnitsDescription };
