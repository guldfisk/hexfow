import { UnitDetails } from "../interfaces/gameObjectDetails.ts";
import React from "react";
import { getImageUrl } from "../image/images.ts";

interface GridItemData {
  unit: UnitDetails;
  enabled: boolean;
}

export const UnitGridItem = ({
  unit,
  onClick,
  onHover,
}: {
  unit: GridItemData;
  onClick: ((unit: GridItemData) => void) | null;
  onHover: ((unit: GridItemData) => void) | null;
}) => {
  return (
    <span className={"text-container unit-thumbnail"}>
      <img
        onMouseEnter={() => (onHover ? onHover(unit) : null)}
        onClick={() => (onClick ? onClick(unit) : null)}
        src={getImageUrl("unit", unit.unit.identifier)}
        className={"unit-thumbnail" + (!unit.enabled ? " grey-image" : "")}
      />
      <div className={"text-top-left"}>{unit.unit.price}</div>
    </span>
  );
};

export const UnitGrid = ({
  units,
  onClick,
  onHover,
}: {
  units: GridItemData[];
  onClick: ((unit: GridItemData) => void) | null;
  onHover: ((unit: GridItemData) => void) | null;
}) => {
  return (
    <div className={"unit-grid"}>
      {units.map((unit) => (
        <UnitGridItem unit={unit} onClick={onClick} onHover={onHover} />
      ))}
    </div>
  );
};
