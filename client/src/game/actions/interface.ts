import {
  Cone,
  ConsecutiveAdjacentHexes,
  DeployArmyDecisionPoint,
  HexHexes,
  HexRing,
  NOfHexes,
  NOfUnits,
  Option,
  RadiatingLine,
  SelectArmyDecisionPoint,
  Tree,
  TriHex,
  Unit,
  UnitOption,
} from "../../interfaces/gameState.ts";
import { CC, Corner, RC } from "../../interfaces/geometry.ts";
import { UnitDetails } from "../../interfaces/gameObjectDetails.ts";

export type TakeAction = (body: { [key: string]: any }) => void;

export interface DelayedActivation {
  optionIndex: number;
  targetIndex: number;
  unit: Unit;
  options: UnitOption[];
}

export type selectionIcon =
  | "ranged_attack"
  | "melee_attack"
  | "activated_ability"
  | "aoe"
  | "menu"
  | "generic";

export interface Action {
  type: selectionIcon;
  sourceOption?: Option;
  description: string;
  do: (localPosition: RC) => void;
}

export interface HexActions {
  actions: Action[];
  sideMenuItems?: Action[];
  highlighted?: boolean;
  blueprintGhost?: string | null;
  hoverTrigger?: (localPosition: RC) => void;
  previewOptions?: UnitOption[] | null;
}

export interface ButtonAction {
  description: string;
  do: () => void;
}

export interface LoadFileAction {
  description: string;
  do: (content: string) => void;
}

export interface ActionSpace {
  hexActions: { [key: string]: HexActions };
  buttonAction: ButtonAction | null;
  loadFileAction?: LoadFileAction | null;
  unitListActions?: {
    units: UnitDetails[];
    onClick: ((unit: UnitDetails) => void) | null;
  } | null;
}

export interface BaseMenuData {
  type: string;
  uncloseable?: boolean;
}

export interface NOfUnitsMenu extends BaseMenuData {
  type: "NOfUnits";
  optionIndex: number;
  selectedUnits: string[];
  targetProfile: NOfUnits;
}

export interface NOfHexesMenu extends BaseMenuData {
  type: "NOfHexes";
  optionIndex: number;
  selectedIndexes: number[];
  targetProfile: NOfHexes;
}

export interface ConsecutiveAdjacentHexesMenu extends BaseMenuData {
  type: "ConsecutiveAdjacentHexes";
  optionIndex: number;
  targetProfile: ConsecutiveAdjacentHexes;
  hovering: CC | null;
}

export interface HexHexesMenu extends BaseMenuData {
  type: "HexHexes";
  optionIndex: number;
  targetProfile: HexHexes;
  hovering: CC | null;
}

export interface HexRingMenu extends BaseMenuData {
  type: "HexRing";
  optionIndex: number;
  targetProfile: HexRing;
  hovering: CC | null;
}

export interface RadiatingLineMenu extends BaseMenuData {
  type: "RadiatingLine";
  optionIndex: number;
  targetProfile: RadiatingLine;
  hovering: CC | null;
}

export interface ConeMenu extends BaseMenuData {
  type: "Cone";
  optionIndex: number;
  targetProfile: Cone;
  hovering: CC | null;
}

export interface TreeMenu extends BaseMenuData {
  type: "Tree";
  optionIndex: number;
  targetProfile: Tree;
  selectedIndexes: number[];
}

export interface ListMenu extends BaseMenuData {
  type: "ListMenu";
  cc: CC;
}

export interface TriHexMenu extends BaseMenuData {
  type: "TriHex";
  optionIndex: number;
  targetProfile: TriHex;
  hovering: Corner | null;
}

export interface SelectArmyMenu extends BaseMenuData {
  type: "SelectArmy";
  decisionPoint: SelectArmyDecisionPoint;
  selectedUnits: UnitDetails[];
  submitted: boolean;
}

export interface ArrangeArmyMenu extends BaseMenuData {
  type: "ArrangeArmy";
  decisionPoint: DeployArmyDecisionPoint;
  units: UnitDetails[];
  unitPositions: { [name: string]: CC };
  swappingPosition: CC | null;
  submitted: boolean;
}

export type MenuData =
  | NOfUnitsMenu
  | NOfHexesMenu
  | TreeMenu
  | ConsecutiveAdjacentHexesMenu
  | HexHexesMenu
  | HexRingMenu
  | RadiatingLineMenu
  | ConeMenu
  | ListMenu
  | TriHexMenu
  | SelectArmyMenu
  | ArrangeArmyMenu;
