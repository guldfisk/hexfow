import { Hex, Status, Unit, UnitStatus } from "./gameState.ts";
import { FacetDetails } from "./gameObjectDetails.ts";

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

export interface HoveredStatusTypes extends BaseHovered {
  type: "statusTypes";
  statuses: string[];
}

export interface HoveredFacet extends BaseHovered {
  type: "facet";
  facet: FacetDetails;
}

export type HoveredDetails =
  | HoveredUnit
  | HoveredBlueprint
  | HoveredHex
  | HoveredStatuses
  | HoveredStatusTypes
  | HoveredFacet;
