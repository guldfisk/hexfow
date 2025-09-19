import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import { CC } from "../../interfaces/geometry.ts";
import { ccEquals, ccToKey, constMultCC, getL } from "../../geometry.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";
import { DeploymentSpec } from "../../interfaces/gameState.ts";
import { mapCoordinates } from "../mapShape.ts";

const defaultDeploymentSpec: DeploymentSpec = {
  max_army_units: 20,
  max_army_points: 120,
  max_deployment_units: 12,
  max_deployment_points: 70,
};

export interface UnitSpec {
  identifier: string;
  allied: boolean;
}

export interface HexSpec {
  terrainType: string;
  unit: UnitSpec | null;
  isObjective: boolean;
  deploymentZoneOf: number | null | undefined;
  statuses: string[];
  cc: CC;
}

interface MapLoaderData {
  show: boolean;
  selected: string | null;
  options: string[];
}

const doubleMirror = (cc: CC): CC => constMultCC(cc, -1);
const singleMirror = (cc: CC) => ({ r: -getL(cc) - cc.h, h: getL(cc) });

type MirrorMode = "single" | "double";

const changeHex = (
  state: MapEditorState,
  cc: CC,
  change: (spec: HexSpec, isMirrored: boolean) => void,
) => {
  const m = state.mirrorMode == "double" ? doubleMirror : singleMirror;
  for (const [idx, cc_] of (ccEquals(cc, m(cc))
    ? [cc]
    : [cc, m(cc)]
  ).entries()) {
    if (!state.mapData[ccToKey(cc_)]) {
      state.mapData[ccToKey(cc_)] = {
        terrainType: "plains",
        unit: null,
        isObjective: false,
        deploymentZoneOf: null,
        statuses: [],
        cc: cc_,
      };
    }
    change(state.mapData[ccToKey(cc_)], idx == 1);
  }
  state.shouldRerender = true;
};

const mainSlice = createSlice({
  name: "mapEditor",
  initialState: {
    mapData: Object.fromEntries(
      mapCoordinates.map((cc) => [
        ccToKey(cc),
        {
          terrainType: "plains",
          unit: null,
          isObjective: false,
          deploymentZoneOf: null,
          statuses: [],
          cc: cc,
        },
      ]),
    ),
    mapName: "new map",
    loaderData: { show: false, selected: null, options: [] },
    shouldRerender: true,
    hoveredCC: null,
    selectedUnitIdentifier: null,
    selectedStatusIdentifier: null,
    gameObjectDetails: null,
    toPoints: 24,
    deploymentSpec: defaultDeploymentSpec,
    mirrorMode: "double",
  } as {
    mapData: { [key: string]: HexSpec };
    mapName: string;
    loaderData: MapLoaderData;
    shouldRerender: boolean;
    hoveredCC: CC | null;
    selectedUnitIdentifier: string | null;
    selectedStatusIdentifier: string | null;
    gameObjectDetails: GameObjectDetails | null;
    toPoints: number;
    deploymentSpec: DeploymentSpec;
    mirrorMode: MirrorMode;
  },
  reducers: {
    loadedImage: (state) => {
      state.shouldRerender = true;
    },
    resetMap: (state) => {
      state.mapData = {
        [ccToKey({ r: 0, h: 0 })]: {
          terrainType: "plains",
          unit: null,
          isObjective: false,
          deploymentZoneOf: null,
          statuses: [],
          cc: { r: 0, h: 0 },
        },
      };
      state.mapName = "new map";
      state.deploymentSpec = defaultDeploymentSpec;
      state.toPoints = 24;
      state.shouldRerender = true;
    },
    loadMap: (
      state,
      action: PayloadAction<{
        name: string;
        scenario: {
          hexes: {
            cc: CC;
            unit: { allied: boolean; identifier: string } | null;
            statuses: string[];
            is_objective: boolean;
            deployment_zone_of: number | null;
            terrain_type: string;
          }[];
          deployment_spec: DeploymentSpec;
          to_points: number;
        };
      }>,
    ) => {
      state.mapData = Object.fromEntries(
        action.payload.scenario.hexes.map((spec) => [
          ccToKey(spec.cc),
          {
            cc: spec.cc,
            unit: spec.unit,
            statuses: spec.statuses,
            isObjective: spec.is_objective,
            deploymentZoneOf: spec.deployment_zone_of,
            terrainType: spec.terrain_type,
          },
        ]),
      );
      state.toPoints = action.payload.scenario.to_points;
      state.deploymentSpec = action.payload.scenario.deployment_spec;
      state.shouldRerender = true;
      state.mapName = action.payload.name;
      state.loaderData.show = false;
    },
    setMapName: (state, action: PayloadAction<string>) => {
      state.mapName = action.payload;
    },
    setMirrorMode: (state, action: PayloadAction<MirrorMode>) => {
      state.mirrorMode = action.payload;
    },
    setShowLoader: (state, action: PayloadAction<boolean>) => {
      state.loaderData.show = action.payload;
    },
    setLoaderSelected: (state, action: PayloadAction<string | null>) => {
      state.loaderData.selected = action.payload;
    },
    setLoaderOptions: (state, action: PayloadAction<string[]>) => {
      state.loaderData.options = action.payload;
    },
    receivedGameObjectDetails: (
      state,
      action: PayloadAction<GameObjectDetails>,
    ) => {
      state.gameObjectDetails = action.payload;
    },
    updateTerrain: (
      state,
      action: PayloadAction<{ cc: CC; terrainType: string }>,
    ) => {
      changeHex(
        state,
        action.payload.cc,
        (spec) => (spec.terrainType = action.payload.terrainType),
      );
    },
    removeHex: (state, action: PayloadAction<CC>) => {
      delete state.mapData[ccToKey(action.payload)];
      delete state.mapData[
        ccToKey(
          (state.mirrorMode == "double" ? doubleMirror : singleMirror)(
            action.payload,
          ),
        )
      ];
      state.shouldRerender = true;
    },
    updateUnit: (
      state,
      action: PayloadAction<{ cc: CC; unitIdentifier: string | null }>,
    ) => {
      changeHex(
        state,
        action.payload.cc,
        (spec, isMirrored) =>
          (spec.unit = action.payload.unitIdentifier
            ? { identifier: action.payload.unitIdentifier, allied: !isMirrored }
            : null),
      );
    },
    toggleDeploymentZone: (state, action: PayloadAction<CC>) => {
      changeHex(
        state,
        action.payload,
        (spec, isMirrored) =>
          (spec.deploymentZoneOf =
            spec.deploymentZoneOf == null ? (isMirrored ? 1 : 0) : null),
      );
    },
    toggleIsObjective: (state, action: PayloadAction<CC>) => {
      changeHex(
        state,
        action.payload,
        (spec) => (spec.isObjective = !spec.isObjective),
      );
    },
    setStatus: (
      state,
      action: PayloadAction<{ cc: CC; status: string | null }>,
    ) => {
      changeHex(
        state,
        action.payload.cc,
        (spec) =>
          (spec.statuses = action.payload.status
            ? [action.payload.status]
            : []),
      );
    },
    renderedGameState: (state) => {
      state.shouldRerender = false;
    },
    setHoveredCC: (state, action: PayloadAction<CC>) => {
      state.hoveredCC = action.payload;
    },
    setSelectedUnitIdentifier: (state, action: PayloadAction<string>) => {
      state.selectedUnitIdentifier = action.payload;
    },
    setSelectedStatusIdentifier: (state, action: PayloadAction<string>) => {
      state.selectedStatusIdentifier = action.payload;
    },
    setDeploymentSpec: (state, action: PayloadAction<DeploymentSpec>) => {
      state.deploymentSpec = action.payload;
    },
    setToPoints: (state, action: PayloadAction<number>) => {
      state.toPoints = action.payload;
    },
  },
});

export const {
  toggleDeploymentZone,
  setMirrorMode,
  loadMap,
  setMapName,
  setShowLoader,
  setLoaderSelected,
  setLoaderOptions,
  loadedImage,
  receivedGameObjectDetails,
  renderedGameState,
  setHoveredCC,
  updateTerrain,
  updateUnit,
  toggleIsObjective,
  setSelectedUnitIdentifier,
  setSelectedStatusIdentifier,
  setStatus,
  setDeploymentSpec,
  setToPoints,
  removeHex,
  resetMap,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type MapEditorState = ReturnType<typeof store.getState>;
export type MapEditorDispatch = typeof store.dispatch;
