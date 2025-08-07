import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import { GameState } from "../interfaces/gameState.ts";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";
import { MenuData, selectionIcon } from "../actions/interface.ts";
import { HoveredDetails } from "../interfaces/details.ts";

const mainSlice = createSlice({
  name: "application",
  initialState: {
    gameState: null,
    shouldRerender: true,
    gameObjectDetails: null,
    detailed: null,
    menuData: null,
    actionPreview: null,
    highlightedCCs: null,
  } as {
    gameState: GameState | null;
    shouldRerender: boolean;
    gameObjectDetails: GameObjectDetails | null;
    detailed: HoveredDetails | null;
    menuData: MenuData | null;
    actionPreview: { [key: string]: selectionIcon[] } | null;
    highlightedCCs: string[] | null;
  },
  reducers: {
    receiveGameState: (state, action: PayloadAction<GameState>) => {
      state.gameState = action.payload;
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
      if (state.menuData) {
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
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
