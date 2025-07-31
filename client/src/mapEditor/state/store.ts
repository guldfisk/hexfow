import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import { CC } from "../../game/interfaces/geometry.ts";
import { ccToKey } from "../../game/geometry.ts";
import { GameObjectDetails } from "../../game/interfaces/gameObjectDetails.ts";

export interface UnitSpec {
  identifier: string;
  allied: boolean;
}

export interface HexSpec {
  terrainType: string;
  unit: UnitSpec | null;
  isObjective: boolean;
  statuses: string[];
  cc: CC;
}

const mainSlice = createSlice({
  name: "mapEditor",
  initialState: {
    mapData: {},
    shouldRerender: true,
    hoveredHex: null,
    selectedUnitIdentifier: null,
    selectedStatusIdentifier: null,
    gameObjectDetails: null,
  } as {
    mapData: { [key: string]: HexSpec };
    shouldRerender: boolean;
    hoveredHex: HexSpec | null;
    selectedUnitIdentifier: string | null;
    selectedStatusIdentifier: string | null;
    gameObjectDetails: GameObjectDetails | null;
  },
  reducers: {
    setMapData: (state, action: PayloadAction<HexSpec[]>) => {
      state.mapData = Object.fromEntries(
        action.payload.map((spec) => [ccToKey(spec.cc), spec]),
      );
      state.shouldRerender = true;
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
      state.mapData[ccToKey(action.payload.cc)].terrainType =
        action.payload.terrainType;
      state.mapData[
        ccToKey({ r: -action.payload.cc.r, h: -action.payload.cc.h })
      ].terrainType = action.payload.terrainType;
      state.shouldRerender = true;
    },
    updateUnit: (
      state,
      action: PayloadAction<{ cc: CC; unitIdentifier: string | null }>,
    ) => {
      state.mapData[ccToKey(action.payload.cc)].unit = action.payload
        .unitIdentifier
        ? { identifier: action.payload.unitIdentifier, allied: true }
        : null;
      state.mapData[
        ccToKey({ r: -action.payload.cc.r, h: -action.payload.cc.h })
      ].unit = action.payload.unitIdentifier
        ? { identifier: action.payload.unitIdentifier, allied: false }
        : null;
      state.shouldRerender = true;
    },
    toggleIsObjective: (state, action: PayloadAction<CC>) => {
      state.mapData[ccToKey(action.payload)].isObjective =
        !state.mapData[ccToKey(action.payload)].isObjective;
      if (!(action.payload.r == 0 && action.payload.h == 0)) {
        state.mapData[
          ccToKey({ r: -action.payload.r, h: -action.payload.h })
        ].isObjective =
          !state.mapData[
            ccToKey({ r: -action.payload.r, h: -action.payload.h })
          ].isObjective;
      }
      state.shouldRerender = true;
    },
    setStatus: (
      state,
      action: PayloadAction<{ cc: CC; status: string | null }>,
    ) => {
      state.mapData[ccToKey(action.payload.cc)].statuses = action.payload.status
        ? [action.payload.status]
        : [];
      state.mapData[
        ccToKey({ r: -action.payload.cc.r, h: -action.payload.cc.h })
      ].statuses = action.payload.status ? [action.payload.status] : [];
      state.shouldRerender = true;
    },
    renderedGameState: (state) => {
      state.shouldRerender = false;
    },
    setHoveredHex: (state, action: PayloadAction<CC>) => {
      state.hoveredHex = state.mapData[ccToKey(action.payload)] || null;
    },
    setSelectedUnitIdentifier: (state, action: PayloadAction<string>) => {
      state.selectedUnitIdentifier = action.payload;
    },
    setSelectedStatusIdentifier: (state, action: PayloadAction<string>) => {
      state.selectedStatusIdentifier = action.payload;
    },
  },
});

export const {
  setMapData,
  receivedGameObjectDetails,
  renderedGameState,
  setHoveredHex,
  updateTerrain,
  updateUnit,
  toggleIsObjective,
  setSelectedUnitIdentifier,
  setSelectedStatusIdentifier,
  setStatus,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type MapEditorState = ReturnType<typeof store.getState>;
export type MapEditorDispatch = typeof store.dispatch;
