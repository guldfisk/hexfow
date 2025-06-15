import { GameState } from "./gameState.ts";
import {GameObjectDetails} from "./gameObjectDetails.ts";

export interface ApplicationState {
  gameState: GameState | null;
  shouldRerender: boolean;
  gameObjectDetails: GameObjectDetails | null;
}
