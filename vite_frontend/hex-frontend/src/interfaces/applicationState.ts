import { GameState } from "./gameState.ts";

export interface ApplicationState {
  gameState: GameState | null;
  shouldRerender: boolean;
}
