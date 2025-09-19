import { ReactNode } from "react";
import { Unit } from "../interfaces/gameState.ts";
import {
  CostAtom,
  EffortCostSet,
  FacetDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../image/images.ts";
import { ModifiedValue } from "./modifiedValue.tsx";

const effortCostAtomToShort = (cost: CostAtom): string => {
  switch (cost.type) {
    case "EnergyCost": {
      return `${cost.amount}E`;
    }
    case "MovementCost": {
      return `${cost.amount}M`;
    }
    case "ExclusiveCost": {
      return `Exclusive`;
    }
  }
};

const effortCostToShort = (cost: EffortCostSet): string =>
  cost.atoms.length ? cost.atoms.map(effortCostAtomToShort).join(" ") : "-";

const getFacetStatLine = (
  facet: FacetDetails,
  unit: Unit | null,
): ReactNode[] => {
  const stats: ReactNode[][] = [];

  if ("combineable" in facet && facet.combineable) {
    stats.push(["combineable"]);
  }
  if ("max_activations" in facet && facet.max_activations != 1) {
    stats.push([
      facet.max_activations === null
        ? "unlimited activations"
        : `${facet.max_activations} max activations`,
    ]);
  }
  if ("cost" in facet && facet.cost.atoms.length) {
    stats.push([`cost: ${effortCostToShort(facet.cost)}`]);
  }
  if ("damage" in facet) {
    stats.push([
      "damage: ",
      <ModifiedValue
        current={
          facet.damage +
          (unit
            ? facet.benefits_from_attack_power
              ? unit.attack_power
              : Math.min(unit.attack_power, 0)
            : 0)
        }
        base={facet.damage}
      />,
    ]);
  }
  if ("range" in facet) {
    stats.push([`range: ${facet.range}`]);
  }
  if ("hidden_target" in facet && facet.hidden_target) {
    stats.push(["hidden target"]);
  }

  const atoms = [];

  for (let i = 0; i < stats.length; i++) {
    atoms.push(stats[i]);
    if (i + 1 < stats.length) {
      atoms.push(" - ");
    }
  }

  return atoms;
};

export const FacetDetailView = ({
  facet,
  unit,
}: {
  facet: FacetDetails;
  unit: Unit | null;
}) => (
  <div className={"facet-details"}>
    <div className={"facet-header"}>
      <img src={getImageUrl("icon", facet.category)} className={"facet-icon"} />
      {facet.name}
    </div>
    <div className={"facet-stats"}>{getFacetStatLine(facet, unit)}</div>
    {"target_explanation" in facet && facet.target_explanation ? (
      <div className={"facet-description"}>{facet.target_explanation}</div>
    ) : null}
    {facet.description ? (
      <div className={"facet-description"}>{facet.description}</div>
    ) : null}
  </div>
);
