import {Hex, Status, Unit, UnitStatus} from "./gameState.ts";

interface BaseHovered {
  type: string;
}

export interface HoveredUnit extends BaseHovered {
  type: "unit";
  unit: Unit;
}

export interface HoveredBlueprint extends BaseHovered {
  type: "blueprint";
  blueprint: string;
}

export interface HoveredHex extends BaseHovered {
  type: "hex";
  hex: Hex;
}

export interface HoveredStatuses extends BaseHovered {
  type: "statuses";
  statuses: Status[] | UnitStatus[];
}

export type HoveredDetails = HoveredUnit | HoveredBlueprint | HoveredHex | HoveredStatuses;
