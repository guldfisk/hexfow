import { UnitDetails } from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../image/images.ts";
import React from "react";

export const sortBlueprints = (a: UnitDetails, b: UnitDetails) => {
  if ((a.price || 0) > (b.price || 0)) {
    return 1;
  }
  if ((b.price || 0) > (a.price || 0)) {
    return -1;
  }
  if (a.identifier > b.identifier) {
    return 1;
  }
  if (b.identifier > b.identifier) {
    return -1;
  }
  return 0;
};

export const UnitListItem = ({
  unit,
  onClick,
  onHover,
}: {
  unit: UnitDetails;
  onClick: ((unit: UnitDetails) => void) | null;
  onHover: ((unit: UnitDetails) => void) | null;
}) => {
  return (
    <div
      className={"unit-list-item"}
      onMouseEnter={() => (onHover ? onHover(unit) : null)}
      onClick={() => (onClick ? onClick(unit) : null)}
    >
      <span>{`${unit.name} - ${unit.price}`}</span>
      <img
        src={getImageUrl("unit", unit.identifier)}
        className={"unit-thumbnail"}
      />
    </div>
  );
};

export const UnitList = ({
  units,
  onClick,
  onHover,
}: {
  units: UnitDetails[];
  onClick: ((unit: UnitDetails) => void) | null;
  onHover: ((unit: UnitDetails) => void) | null;
}) => {
  return (
    <div className={"unit-list"}>
      {units.map((unit) => (
        <UnitListItem unit={unit} onClick={onClick} onHover={onHover} />
      ))}
    </div>
  );
};
