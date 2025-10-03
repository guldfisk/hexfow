import { CC, Corner } from "./geometry.ts";
import { EffortFacetDetails } from "./gameObjectDetails.ts";

// TODO refactor this shit

export type Size = 0 | 1 | 2;

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
  max_health: number;
  damage: number;
  speed: number;
  sight: number;
  max_energy: number;
  energy: number;
  armor: number;
  attack_power: number;
  size: Size;
  exhausted: boolean;
  is_ghost: boolean;
  statuses: UnitStatus[];
}

export interface Hex {
  cc: CC;
  terrain: string;
  is_objective: boolean;
  captured_by: string | boolean;
  visible: boolean;
  last_visible_round: number | null;
  unit: Unit | null;
  statuses: Status[];
}

export interface Map {
  hexes: Hex[];
}

export interface ActiveUnitContext {
  unit: Unit;
  movement_points: number;
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
    select_count: number;
    min_count: number | null;
    labels: string[];
  };
}

export interface NOfHexes extends TargetProfileBase {
  type: "NOfHexes";
  values: {
    hexes: { cc: CC }[];
    select_count: number;
    min_count: number | null;
    labels: string[];
  };
}

export interface ConsecutiveAdjacentHexes extends TargetProfileBase {
  type: "ConsecutiveAdjacentHexes";
  values: { adjacent_to: CC; arm_length: number };
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
  values: { from_hex: CC; to_hexes: CC[]; length: number };
}

export interface Cone extends TargetProfileBase {
  type: "Cone";
  values: { from_hex: CC; to_hexes: CC[]; arm_lengths: number[] };
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
  values: { root_node: TreeNode };
}

export interface TriHex extends TargetProfileBase {
  type: "TriHex";
  values: { corners: Corner[] };
}

export type TargetProfile =
  | OneOfUnits
  | NOfUnits
  | OneOfHexes
  | NOfHexes
  | NoTarget
  | ConsecutiveAdjacentHexes
  | HexHexes
  | HexRing
  | RadiatingLine
  | Cone
  | Tree
  | TriHex;

export interface OptionBase {
  type: string;
  values: { [key: string]: any };
  target_profile: TargetProfile;
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
    actions_preview: { [key: string]: UnitOption[] };
  };
}

export type Option = UnitOption | ActivateUnitOption;

export interface SelectOptionDecisionPoint extends BaseDecision {
  type: "SelectOptionDecisionPoint";
  payload: { options: Option[] };
}

export interface DeploymentSpec {
  max_army_units: number;
  max_army_points: number;
  max_deployment_units: number;
  max_deployment_points: number;
}

export interface SelectArmyDecisionPoint extends BaseDecision {
  type: "SelectArmyDecisionPoint";
  payload: {
    deployment_zone: CC[];
    deployment_spec: DeploymentSpec;
  };
}

export interface DeployArmyDecisionPoint extends BaseDecision {
  type: "DeployArmyDecisionPoint";
  payload: {
    units: string[];
    deployment_zone: CC[];
    deployment_spec: DeploymentSpec;
  };
}

export interface SelectOptionAtHexDecisionPoint extends BaseDecision {
  type: "SelectOptionAtHexDecisionPoint";
  payload: {
    hex: CC;
    options: string[];
  };
}

export type Decision =
  | SelectOptionDecisionPoint
  | SelectArmyDecisionPoint
  | DeployArmyDecisionPoint
  | SelectOptionAtHexDecisionPoint;

export interface LogLineComponentBase {
  type: string;
}

export interface UnitLogLineComponent extends LogLineComponentBase {
  type: "unit";
  identifier: string;
  blueprint: string;
  controller: string;
  cc: CC;
}

export interface BlueprintLogLineComponent extends LogLineComponentBase {
  type: "blueprint";
  blueprint: string;
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
  items: (
    | UnitLogLineComponent
    | HexLogLineComponent
    | BlueprintLogLineComponent
  )[];
}

export interface PlayerLogLineComponent extends LogLineComponentBase {
  type: "player";
  name: string;
}

export type LogLineComponent =
  | UnitLogLineComponent
  | HexLogLineComponent
  | FacetLogLineComponent
  | StatusLogLineComponent
  | ListLogLineComponent
  | StringLogLineComponent
  | PlayerLogLineComponent
  | BlueprintLogLineComponent;

export type LogLine = [number, LogLineComponent[]];

export interface Player {
  name: string;
  points: number;
}

export interface GameState {
  player: string;
  target_points: number;
  players: Player[];
  round: number;
  map: Map;
  event_log: string[];
  decision: Decision | null;
  active_unit_context: ActiveUnitContext | null;
  logs: LogLine[];
  new_logs: LogLine[];
}
