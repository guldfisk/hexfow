import { CC } from "./geometry.ts";
import { EffortFacetDetails } from "./gameObjectDetails.ts";

// TODO refactor this shit

export type Size = "S" | "M" | "L";

export interface Status {
  type: string;
  duration: number | null;
  stacks: number | null;
}

export type Intention = "buff" | "debuff" | "neutral";

export interface UnitStatus extends Status {
  intention: Intention;
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
  attackPower: number;
  size: Size;
  exhausted: boolean;
  isGhost: boolean;
  statuses: UnitStatus[];
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
  values: {
    units: { id: string }[];
    selectCount: number;
    minCount: number | null;
    labels: string[];
  };
}

export interface ConsecutiveAdjacentHexes extends TargetProfileBase {
  type: "ConsecutiveAdjacentHexes";
  values: { adjacentTo: CC; armLength: number };
}

export interface HexHexes extends TargetProfileBase {
  type: "HexHexes";
  values: { centers: CC[]; radius: number };
}

export interface HexRing extends TargetProfileBase {
  type: "HexRing";
  values: { centers: CC[]; radius: number };
}

export interface RadiatingLine extends TargetProfileBase {
  type: "RadiatingLine";
  values: { fromHex: CC; toHexes: CC[]; length: number };
}

export interface Cone extends TargetProfileBase {
  type: "Cone";
  values: { fromHex: CC; toHexes: CC[]; armLengths: number[] };
}

export interface TreeNode {
  options: [
    { type: "unit"; id: string } | { type: "hex"; cc: CC },
    TreeNode | null,
  ][];
  label: string;
}

export interface Tree extends TargetProfileBase {
  type: "Tree";
  values: { rootNode: TreeNode };
}

export type TargetProfile =
  | OneOfUnits
  | NOfUnits
  | OneOfHexes
  | NoTarget
  | ConsecutiveAdjacentHexes
  | HexHexes
  | HexRing
  | RadiatingLine
  | Cone
  | Tree;

export interface OptionBase {
  type: string;
  values: { [key: string]: any };
  targetProfile: TargetProfile;
}

export interface SkipOption extends OptionBase {
  type: "SkipOption";
  values: {};
}

export interface MoveOption extends OptionBase {
  type: "MoveOption";
  values: {};
}

export interface EffortOption extends OptionBase {
  type: "EffortOption";
  values: { facet: EffortFacetDetails };
}

export type UnitOption = SkipOption | MoveOption | EffortOption;

export interface ActivateUnitOption extends OptionBase {
  type: "ActivateUnitOption";
  values: {
    actionsPreview: { [key: string]: UnitOption[] };
  };
}

export type Option = UnitOption | ActivateUnitOption;

export interface SelectOptionDecisionPoint extends BaseDecision {
  type: "SelectOptionDecisionPoint";
  payload: { options: Option[] };
}

export type Decision = SelectOptionDecisionPoint;

export interface LogLineComponentBase {
  type: string;
}

export interface UnitLogLineComponent extends LogLineComponentBase {
  type: "unit";
  identifier: string;
  blueprint: string;
  controller: string;
}

export interface HexLogLineComponent extends LogLineComponentBase {
  type: "hex";
  cc: CC;
}

export interface FacetLogLineComponent extends LogLineComponentBase {
  type: "facet";
  identifier: string;
}

export interface StatusLogLineComponent extends LogLineComponentBase {
  type: "status";
  identifier: string;
}

export interface StringLogLineComponent extends LogLineComponentBase {
  type: "string";
  message: string;
}

export interface ListLogLineComponent extends LogLineComponentBase {
  type: "list";
  items: (UnitLogLineComponent | HexLogLineComponent)[];
}

export type LogLineComponent =
  | UnitLogLineComponent
  | HexLogLineComponent
  | FacetLogLineComponent
  | StatusLogLineComponent
  | ListLogLineComponent
  | StringLogLineComponent;

export type LogLine = [number, LogLineComponent[]];

export interface Player {
  name: string;
  points: number;
}

export interface GameState {
  player: string;
  targetPoints: number;
  players: Player[];
  round: number;
  map: Map;
  eventLog: string[];
  decision: Decision | null;
  activeUnitContext: ActiveUnitContext | null;
  logs: LogLine[];
}
