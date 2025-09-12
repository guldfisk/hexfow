import { GameState } from "./gameState.ts";

export interface BaseMessage {
  message_type: string;
}

export interface ErrorMessage extends BaseMessage {
  message_type: "error";
}

export interface GameStateMessage extends BaseMessage {
  message_type: "game_state";
  count: number;
  game_state: GameState;
}

export type Message = ErrorMessage | GameStateMessage;
