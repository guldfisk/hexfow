export interface CC {
  r: number;
  h: number;
}

export interface Unit {
  id: string;
  blueprint: string;
  controller: string;
  maxHealth: number;
  damage: number;
  speed: number;
  sight: number;
  max_energy: number;
  energy: number;
  size: string;
  exhausted: boolean;
}

export interface Hex {
  cc: CC;
  terrain: string;
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
  round: number;
  map: Map;
  eventLog: string[];
  decision: { [key: string]: any } | null;
  activeUnitContext: ActiveUnitContext | null;
}
