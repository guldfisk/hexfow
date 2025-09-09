import { Assets, Texture } from "pixi.js";

export type ResourceType = "icon" | "unit" | "status"|'terrain';

export const getImageUrl = (
  resourceType: ResourceType,
  resourceIdentifier: string,
): string => {
  switch (resourceType) {
    case "icon":
      return `/src/images/icons/${resourceIdentifier}_icon.png`;
    case "unit":
      return `/src/images/units/${resourceIdentifier}.png`;
    case "status":
      return `/src/images/statuses/${resourceIdentifier}.png`;
    case "terrain":
      return `/src/images/terrain/terrain_${resourceIdentifier}_square.png`;
  }
};

export const getImage = async (
  resourceType: ResourceType,
  resourceIdentifier: string,
): Promise<Texture> =>
  Assets.load(getImageUrl(resourceType, resourceIdentifier));
