import { CC } from "./geometry.ts";
import { EffortFacetDetails } from "./gameObjectDetails.ts";

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
  lastVisibleRound: number | null;
  unit: Unit | null;
  statuses: Status[];
}

export interface Map {
  hexes: Hex[];
}

export interface ActiveUnitContext {
  unit: Unit;
  movementPoints: number;
}

export interface BaseDecision {
  explanation: string;
  type: string;
  payload: { [key: string]: any };
}

export interface TargetProfileBase {
  type: string;
  values: { [key: string]: any };
}

export interface OneOfHexes extends TargetProfileBase {
  type: "OneOfHexes";
  values: { options: CC[] };
}

export interface OneOfUnits extends TargetProfileBase {
  type: "OneOfUnits";
  values: { units: { id: string }[] };
}

export interface NoTarget extends TargetProfileBase {
  type: "NoTarget";
  values: {};
}

export interface NOfUnits extends TargetProfileBase {
  type: "NOfUnits";
  values: { units: { id: string }[]; selectCount: number; labels: string[] };
}

export type TargetProfile = OneOfUnits | NOfUnits | OneOfHexes | NoTarget;

export interface OptionBase {
  type: string;
  values: { [key: string]: any };
  targetProfile: TargetProfile;
}

export interface EffortOption extends OptionBase {
  type: "EffortOption";
  values: { facet: EffortFacetDetails };
}

export type Option = EffortOption;

export interface SelectOptionDecisionPoint extends BaseDecision {
  type: "SelectOptionDecisionPoint";
  payload: { options: Option[] };
}

export type Decision = SelectOptionDecisionPoint;

export interface GameState {
  player: string;
  round: number;
  map: Map;
  eventLog: string[];
  decision: Decision | null;
  activeUnitContext: ActiveUnitContext | null;
}
