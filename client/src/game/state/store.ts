import { configureStore, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { GameState } from "../interfaces/gameState.ts";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";
import { ActionSpace, MenuData, selectionIcon } from "../actions/interface.ts";
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
    setActionPreview: (state, action: PayloadAction<ActionSpace | null>) => {
      state.actionPreview = action.payload
        ? Object.fromEntries(
            Object.entries(action.payload).map(([cc, hexActions]) => [
              cc,
              hexActions.actions.map((action) => action.type),
            ]),
          )
        : null;
      state.shouldRerender = true;
    },
  },
});

export const {
  receiveGameState,
  renderedGameState,
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
});

export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
