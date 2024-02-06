import { HexCoord } from "./types";

export type TerrainType = "hill" | "mountain";
export type HexData = { terrainType: TerrainType };
export type MapData = Map<HexCoord, HexData>;

export const mapData: MapData = new Map();

mapData.set({ r: 0, h: 0 }, { terrainType: "hill" });
mapData.set({ r: 0, h: 1 }, { terrainType: "mountain" });

type RemoteHex = { position: [number, number], terrain_type: TerrainType};
type RemoteMap = { hexes: RemoteHex[] };

export const deserializeMap = (data: RemoteMap): MapData => {
  const map: MapData = new Map();
  data.hexes.forEach((remoteHex) =>
    map.set(
      { r: remoteHex.position[0], h: remoteHex.position[1] },
      { terrainType: remoteHex.terrain_type },
    ),
  );
  return map;
};
