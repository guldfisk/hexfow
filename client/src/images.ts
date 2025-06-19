export type ResourceType = "icon" | "unit";

export const getImageUrl = (
  resourceType: ResourceType,
  resourceIdentifier: string,
): string => {
  switch (resourceType) {
    case "icon":
      return `/src/images/icons/${resourceIdentifier}_icon.png`;
    case "unit":
      return `/src/images/units/${resourceIdentifier}_small.png`;
  }
};
