import { Assets, Texture } from "pixi.js";

export type ResourceType = "icon" | "unit" | "status";

export const getImageUrl = (
  resourceType: ResourceType,
  resourceIdentifier: string,
): string => {
  switch (resourceType) {
    case "icon":
      return `/src/images/icons/${resourceIdentifier}_icon.png`;
    case "unit":
      return `/src/images/units/${resourceIdentifier}_small.png`;
    case "status":
      return `/src/images/statuses/${resourceIdentifier}.png`;
  }
};

export const getImage = async (
  resourceType: ResourceType,
  resourceIdentifier: string,
): Promise<Texture> =>
  Assets.load(getImageUrl(resourceType, resourceIdentifier));
