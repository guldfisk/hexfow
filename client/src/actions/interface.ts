import {
  ConsecutiveAdjacentHexes,
  HexHexes,
  NOfUnits,
  RadiatingLine,
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
}

export type CCkey = string;

export type ActionSpace = { [key: CCkey]: HexActions };

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
  hovering: number | null;
}

export interface HexHexesMenu extends BaseMenuData {
  type: "HexHexes";
  optionIndex: number;
  targetProfile: HexHexes;
  hovering: CC | null;
}

export interface RadiatingLineMenu extends BaseMenuData {
  type: "RadiatingLine";
  optionIndex: number;
  targetProfile: RadiatingLine;
  hovering: CC | null;
}

export interface ListMenu extends BaseMenuData {
  type: "ListMenu";
  cc: CC;
}

export type MenuData =
  | NOfUnitsMenu
  | ConsecutiveAdjacentHexesMenu
  | HexHexesMenu
  | RadiatingLineMenu
  | ListMenu;
