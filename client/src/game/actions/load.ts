import { activateMenu, store } from "../state/store.ts";
import { SelectArmyDecisionPoint } from "../../interfaces/gameState.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";

export const loadArmy = (
  armyContent: string,
  decision: SelectArmyDecisionPoint,
  gameObjectDetails: GameObjectDetails,
) =>
  store.dispatch(
    activateMenu({
      type: "SelectArmy",
      decisionPoint: decision,
      selectedUnits: armyContent
        .split("\n")
        .filter((id) => id in gameObjectDetails.units)
        .map((name) => gameObjectDetails.units[name]),
      submitted: false,
      uncloseable: true,
    }),
  );
