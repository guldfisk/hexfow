import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import { GameState } from "../../interfaces/gameState.ts";
import { GameObjectDetails } from "../../interfaces/gameObjectDetails.ts";
import { DelayedActivation, MenuData } from "../actions/interface.ts";
import { HoveredDetails } from "../../interfaces/details.ts";
import { deepEquals } from "../utils/equals.ts";
import { GameStateMessage } from "../../interfaces/messages.ts";
import { getAdditionalDetails } from "../../details/additional.ts";

const mainSlice = createSlice({
  name: "application",
  initialState: {
    gameState: null,
    gameStateId: 0,
    shouldRerender: true,
    gameObjectDetails: null,
    detailed: null,
    menuData: null,
    delayedActivation: null,
    highlightedCCs: null,
    showCoordinates: false,
    additionalDetailsIndex: null,
  } as {
    gameState: GameState | null;
    gameStateId: number;
    shouldRerender: boolean;
    gameObjectDetails: GameObjectDetails | null;
    detailed: HoveredDetails | null;
    menuData: MenuData | null;
    delayedActivation: DelayedActivation | null;
    highlightedCCs: string[] | null;
    showCoordinates: boolean;
    additionalDetailsIndex: number | null;
  },
  reducers: {
    receiveGameState: (state, action: PayloadAction<GameStateMessage>) => {
      state.gameState = action.payload.game_state;
      state.gameStateId = action.payload.count;
      state.menuData = null;
      state.delayedActivation = null;
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
      state.additionalDetailsIndex = null;
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
      state.delayedActivation = null;
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
    setDelayedActivation: (state, action: PayloadAction<DelayedActivation>) => {
      state.delayedActivation = action.payload;
      state.shouldRerender = true;
    },
    toggleShowCoordinates: (state) => {
      state.showCoordinates = !state.showCoordinates;
      state.shouldRerender = true;
    },
    incrementAdditionalDetailsIndex: (state) => {
      if (state.gameObjectDetails && state.detailed) {
        const amount = getAdditionalDetails(
          state.detailed,
          state.gameObjectDetails,
        ).length;
        if (!amount) {
          return;
        }
        if (state.additionalDetailsIndex === null) {
          state.additionalDetailsIndex = 0;
        } else if (state.additionalDetailsIndex >= amount - 1) {
          state.additionalDetailsIndex = null;
        } else {
          state.additionalDetailsIndex += 1;
        }
      }
    },
    setAdditionalDetailsIndex: (
      state,
      action: PayloadAction<number | null>,
    ) => {
      state.additionalDetailsIndex = action.payload;
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
  setDelayedActivation,
  toggleShowCoordinates,
  setAdditionalDetailsIndex,
  incrementAdditionalDetailsIndex,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
