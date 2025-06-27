import { configureStore, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { GameState, Unit } from "../interfaces/gameState.ts";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";
import { MenuData } from "../actions/interface.ts";

const mainSlice = createSlice({
  name: "application",
  initialState: {
    gameState: null,
    shouldRerender: true,
    gameObjectDetails: null,
    hoveredUnit: null,
    menuData: null,
  } as {
    gameState: GameState | null;
    shouldRerender: boolean;
    gameObjectDetails: GameObjectDetails | null;
    hoveredUnit: Unit | null;
    menuData: MenuData | null;
  },
  reducers: {
    receiveGameState: (state, action: PayloadAction<GameState>) => {
      state.gameState = action.payload;
      state.menuData = null;
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
    hoverUnit: (state, action: PayloadAction<Unit>) => {
      state.hoveredUnit = action.payload;
    },
    activateMenu: (state, action: PayloadAction<MenuData>) => {
      state.menuData = action.payload;
      state.shouldRerender = true;
    },
    advanceMenu: (
      state,
      action: PayloadAction<MenuData>,
    ) => {
      if (state.menuData) {
        state.menuData = action.payload;
        state.shouldRerender = true;
      }
    },
    deactivateMenu: (state) => {
      state.menuData = null;
      state.shouldRerender = true;
    },
  },
});

export const {
  receiveGameState,
  renderedGameState,
  receivedGameObjectDetails,
  hoverUnit,
  activateMenu,
  advanceMenu,
  deactivateMenu,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
});

export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
