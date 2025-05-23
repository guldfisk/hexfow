import { GameState } from "./gameState.ts";

export interface ApplicationState {
  gameState: GameState;
  shouldRerender: boolean;
}
