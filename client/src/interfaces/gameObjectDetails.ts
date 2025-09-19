export interface BaseFacetDetails {
  name: string;
  identifier: string;
  category: string;
  description: string | null;
  related_statuses: string[];
  related_units: string[];
}

export interface AbstractCostAtom {
  type: string;
}

export interface MovementCostAtom {
  type: "MovementCost";
  amount: number;
}

export interface EnergyCostAtom {
  type: "EnergyCost";
  amount: number;
}
export interface ExclusiveCostAtom {
  type: "ExclusiveCost";
}

export type CostAtom = MovementCostAtom | EnergyCostAtom | ExclusiveCostAtom;

export interface EffortCostSet {
  atoms: CostAtom[];
}

export interface EffortFacetDetailsBase extends BaseFacetDetails {
  cost: EffortCostSet;
  combineable: boolean;
  max_activations: number | null;
}

interface SingleTargetAttackDetails extends EffortFacetDetailsBase {
  damage: number;
  ap: number;
  benefits_from_attack_power: boolean;
}

export interface MeleeAttackFacetDetails extends SingleTargetAttackDetails {
  category: "melee_attack";
}
export interface RangedAttackFacetDetails extends SingleTargetAttackDetails {
  category: "ranged_attack";
  range: number;
}

export interface ActivatedAbilityFacetDetails extends EffortFacetDetailsBase {
  category: "activated_ability";
  target_explanation: string | null;
  hidden_target: boolean;
}

export interface StaticAbilityFacetDetails extends BaseFacetDetails {
  category: "static_ability";
}

export type EffortFacetDetails =
  | MeleeAttackFacetDetails
  | RangedAttackFacetDetails
  | ActivatedAbilityFacetDetails;

export type FacetDetails = EffortFacetDetails | StaticAbilityFacetDetails;

export interface UnitDetails {
  identifier: string;
  name: string;
  health: number;
  speed: number;
  sight: number;
  armor: number;
  energy: number;
  size: number;
  facets: string[];
  price: number | null;
  max_count: number;
  flavor: string | null;
}

export interface TerrainDetails {
  identifier: string;
  name: string;
  description: string | null;
  related_statuses: string[];
  is_water: boolean;
  is_high_ground: boolean;
  blocks_vision: boolean;
}

export type StatusCategory = "unit" | "hex";

export interface StatusDetails {
  identifier: string;
  name: string;
  category: StatusCategory;
  description: string | null;
  related_statuses: string[];
  related_units: string[];
  stacking_info: string;
  dispellable: boolean;
}

export interface GameObjectDetails {
  units: { [identifier: string]: UnitDetails };
  terrain: { [identifier: string]: TerrainDetails };
  statuses: { [identifier: string]: StatusDetails };
  facets: { [identifier: string]: FacetDetails };
}
