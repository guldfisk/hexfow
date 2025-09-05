import { GameState } from "./gameState.ts";

export interface BaseMessage {
  messageType: string;
}

export interface ErrorMessage extends BaseMessage {
  messageType: "error";
}

export interface GameStateMessage extends BaseMessage {
  messageType: "game_state";
  count: number;
  gameState: GameState;
}

export type Message = ErrorMessage | GameStateMessage;
