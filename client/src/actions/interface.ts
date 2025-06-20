import { NOfUnits } from "../interfaces/gameState.ts";

export type selectionIcon =
  | "ranged_attack"
  | "melee_attack"
  | "activated_ability"
  | "generic";

export interface Action {
  type: selectionIcon;
  do: () => void;
}

export interface HexActions {
  actions: Action[];
  highlighted?: boolean;
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

export type MenuData = NOfUnitsMenu;
