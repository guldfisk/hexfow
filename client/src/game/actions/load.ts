import { activateMenu, store } from "../state/store.ts";
import { DeployArmyDecisionPoint } from "../../interfaces/gameState.ts";
import {GameObjectDetails} from "../../interfaces/gameObjectDetails.ts";

export const loadArmy = (
  armyContent: string,
  decision: DeployArmyDecisionPoint,
  gameObjectDetails: GameObjectDetails
) =>
  store.dispatch(
    activateMenu({
      type: "ArrangeArmy",
      decisionPoint: decision,
      unitPositions: Object.fromEntries(
        armyContent
          .split("\n")
          .filter((id) => id in gameObjectDetails.units)
          .map((name, idx) => [name, decision.payload.deploymentZone[idx]]),
      ),
      swappingPosition: null,
      submitted: false,
      uncloseable: true,
    }),
  );
