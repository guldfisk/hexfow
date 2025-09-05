import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import { GameState } from "../../interfaces/gameState.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";
import { MenuData, selectionIcon } from "../actions/interface.ts";
import { HoveredDetails } from "../../interfaces/details.ts";
import { deepEquals } from "../utils/equals.ts";
import { GameStateMessage } from "../../interfaces/messages.ts";

const mainSlice = createSlice({
  name: "application",
  initialState: {
    gameState: null,
    gameStateId: 0,
    shouldRerender: true,
    gameObjectDetails: null,
    detailed: null,
    menuData: null,
    actionPreview: null,
    highlightedCCs: null,
    showCoordinates: false,
  } as {
    gameState: GameState | null;
    gameStateId: number;
    shouldRerender: boolean;
    gameObjectDetails: GameObjectDetails | null;
    detailed: HoveredDetails | null;
    menuData: MenuData | null;
    actionPreview: { [key: string]: selectionIcon[] } | null;
    highlightedCCs: string[] | null;
    showCoordinates: boolean;
  },
  reducers: {
    receiveGameState: (state, action: PayloadAction<GameStateMessage>) => {
      state.gameState = action.payload.gameState;
      state.gameStateId = action.payload.count;
      state.menuData = null;
      state.actionPreview = null;
      state.highlightedCCs = null;
      state.shouldRerender = true;
    },
    renderedGameState: (state) => {
      state.shouldRerender = false;
    },
    loadedImage: (state) => {
      state.shouldRerender = true;
    },
    receivedGameObjectDetails: (
      state,
      action: PayloadAction<GameObjectDetails>,
    ) => {
      state.gameObjectDetails = action.payload;
    },
    hoverDetail: (state, action: PayloadAction<HoveredDetails>) => {
      state.detailed = action.payload;
    },
    activateMenu: (state, action: PayloadAction<MenuData>) => {
      state.menuData = action.payload;
      state.highlightedCCs = null;
      state.shouldRerender = true;
    },
    advanceMenu: (state, action: PayloadAction<MenuData>) => {
      if (state.menuData && !deepEquals(state.menuData, action.payload)) {
        state.menuData = action.payload;
        state.highlightedCCs = null;
        state.shouldRerender = true;
      }
    },
    deactivateMenu: (state) => {
      state.menuData = null;
      state.shouldRerender = true;
    },
    highlightCCs: (state, action: PayloadAction<string[]>) => {
      state.highlightedCCs = action.payload;
      state.shouldRerender = true;
    },
    removeCCHighlight: (state) => {
      state.highlightedCCs = null;
      state.shouldRerender = true;
    },
    setActionPreview: (
      state,
      action: PayloadAction<{ [key: string]: selectionIcon[] } | null>,
    ) => {
      if (!!action.payload || !!state.actionPreview) {
        state.shouldRerender = true;
      }
      state.actionPreview = action.payload;
    },
    toggleShowCoordinates: (state) => {
      state.showCoordinates = !state.showCoordinates;
      state.shouldRerender = true;
    },
  },
});

export const {
  receiveGameState,
  renderedGameState,
  loadedImage,
  receivedGameObjectDetails,
  hoverDetail,
  activateMenu,
  advanceMenu,
  deactivateMenu,
  highlightCCs,
  removeCCHighlight,
  setActionPreview,
  toggleShowCoordinates,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
