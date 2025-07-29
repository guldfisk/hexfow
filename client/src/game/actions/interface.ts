import {
  Cone,
  ConsecutiveAdjacentHexes,
  HexHexes,
  HexRing,
  NOfUnits,
  RadiatingLine,
  Tree,
  UnitOption,
} from "../interfaces/gameState.ts";
import { CC } from "../interfaces/geometry.ts";

export type selectionIcon =
  | "ranged_attack"
  | "melee_attack"
  | "activated_ability"
  | "aoe"
  | "menu"
  | "generic";

export interface Action {
  type: selectionIcon;
  description: string;
  do: () => void;
}

export interface HexActions {
  actions: Action[];
  sideMenuItems?: Action[];
  highlighted?: boolean;
  hoverTrigger?: () => void;
  previewOptions?: UnitOption[] | null;
}

export type ActionSpace = { [key: string]: HexActions };

export interface BaseMenuData {
  type: string;
}

export interface NOfUnitsMenu extends BaseMenuData {
  type: "NOfUnits";
  optionIndex: number;
  selectedUnits: string[];
  targetProfile: NOfUnits;
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

export type MenuData =
  | NOfUnitsMenu
  | TreeMenu
  | ConsecutiveAdjacentHexesMenu
  | HexHexesMenu
  | HexRingMenu
  | RadiatingLineMenu
  | ConeMenu
  | ListMenu;
