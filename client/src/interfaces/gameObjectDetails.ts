export interface BaseFacetDetails {
  name: string;
  identifier: string;
  category: string;
  description: string | null;
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
  small_image: string;
  health: number;
  speed: number;
  sight: number;
  armor: number;
  energy: number;
  size: number;
  aquatic: boolean;
  facets: FacetDetails[];
  price: number;
}

export type UnitsDetails = { [identifier: string]: UnitDetails };

export interface TerrainDetails {
  identifier: string;
  name: string;
  image: string;
}

export type TerrainsDetails = { [identifier: string]: TerrainDetails };

export interface StatusDetails {
  identifier: string;
  name: string;
  image: string;
}

export type StatusesDetails = { [identifier: string]: StatusDetails };

export interface GameObjectDetails {
  units: UnitsDetails;
  terrain: TerrainsDetails;
  statuses: StatusesDetails;
}
