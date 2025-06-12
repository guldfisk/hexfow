import { CC } from "./geometry.ts";

export type Size = "S" | "M" | "L";

export interface Status {
  type: string;
  duration: number | null;
  stacks: number | null;
}

export interface Unit {
  id: string;
  blueprint: string;
  controller: string;
  maxHealth: number;
  damage: number;
  speed: number;
  sight: number;
  maxEnergy: number;
  energy: number;
  armor: number;
  size: Size;
  exhausted: boolean;
  statuses: Status[];
}

export interface Hex {
  cc: CC;
  terrain: string;
  isObjective: boolean;
  visible: boolean;
  unit: Unit | null;
}

export interface Map {
  hexes: Hex[];
}

export interface ActiveUnitContext {
  unit: Unit;
  movementPoints: number;
}

export interface GameState {
  player: string;
  round: number;
  map: Map;
  eventLog: string[];
  decision: { [key: string]: any } | null;
  activeUnitContext: ActiveUnitContext | null;
}
