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
  remaining_time?: number;
  grace?: number;
}

export interface GameResultMessage extends BaseMessage {
  message_type: "game_result";
  winner: string;
  reason: string;
}

export type Message = ErrorMessage | GameStateMessage | GameResultMessage;
