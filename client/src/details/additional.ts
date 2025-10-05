import { HoveredDetails } from "../interfaces/details.ts";
import {
  GameObjectDetails,
  UnitDetails,
} from "../interfaces/gameObjectDetails.ts";
import { traverseStatuses } from "../components/statuses.ts";

export const getRelatedStatuses = (
  unitDetails: UnitDetails,
  gameObjectDetails: GameObjectDetails,
): string[] => {
  const relatedStatuses: string[] = [];
  for (const facetName of unitDetails.facets) {
    for (const status of gameObjectDetails.facets[facetName].related_statuses) {
      if (!relatedStatuses.includes(status)) {
        relatedStatuses.push(status);
        traverseStatuses(status, gameObjectDetails, relatedStatuses);
      }
    }
  }
  return relatedStatuses;
};

const findRelatedUnits = (
  blueprintIdentifier: string,
  gameObjectDetails: GameObjectDetails,
  seen: string[],
): string[] => {
  for (const facetIdentifier of gameObjectDetails.units[blueprintIdentifier]
    .facets) {
    for (const unitIdentifier of gameObjectDetails.facets[facetIdentifier]
      .related_units) {
      if (!seen.includes(unitIdentifier)) {
        seen.push(unitIdentifier);
        findRelatedUnits(unitIdentifier, gameObjectDetails, seen);
      }
    }
    for (const statusIdentifier of gameObjectDetails.facets[facetIdentifier]
      .related_statuses) {
      for (const unitIdentifier of gameObjectDetails.statuses[statusIdentifier]
        .related_units)
        if (!seen.includes(unitIdentifier)) {
          seen.push(unitIdentifier);
          findRelatedUnits(unitIdentifier, gameObjectDetails, seen);
        }
    }
  }
  return seen;
};

export const getAdditionalDetails = (
  detail: HoveredDetails,
  gameObjectDetails: GameObjectDetails,
): HoveredDetails[] => {
  const details: HoveredDetails[] = [];
  if (detail.type == "unit" || detail.type == "blueprint") {
    const unitDetails =
      gameObjectDetails.units[
        detail.type == "unit" ? detail.unit.blueprint : detail.blueprint
      ];
    for (const relatedId of findRelatedUnits(
      unitDetails.identifier,
      gameObjectDetails,
      [],
    )) {
      details.push({ type: "blueprint", blueprint: relatedId });
    }

    const relatedStatuses = getRelatedStatuses(unitDetails, gameObjectDetails);
    if (
      relatedStatuses.length &&
      relatedStatuses.length + unitDetails.facets.length > 6
    ) {
      details.push({ type: "statusTypes", statuses: relatedStatuses });
    }
  } else if (detail.type == "statuses") {
    const seen: string[] = [];
    for (const status of detail.statuses) {
      for (const unitIdentifier of gameObjectDetails.statuses[status.type]
        .related_units) {
        if (!seen.includes(unitIdentifier)) {
          seen.push(unitIdentifier);
          findRelatedUnits(unitIdentifier, gameObjectDetails, seen);
        }
      }
    }
    for (const unitIdentifier of seen) {
      details.push({ type: "blueprint", blueprint: unitIdentifier });
    }
  } else if (detail.type == "facet") {
    const blueprints = Object.values(gameObjectDetails.units).filter((unit) =>
      unit.facets.includes(detail.facet.identifier),
    );
    const seen: string[] = [];
    for (const blueprint of blueprints) {
      seen.push(blueprint.identifier);
    }
    for (const blueprint of blueprints) {
      findRelatedUnits(blueprint.identifier, gameObjectDetails, seen);
    }
    for (const unitIdentifier of seen) {
      details.push({ type: "blueprint", blueprint: unitIdentifier });
    }
  }
  return details;
};
