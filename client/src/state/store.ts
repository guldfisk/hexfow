import { configureStore, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { GameState, Unit } from "../interfaces/gameState.ts";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";

const counterSlice = createSlice({
  name: "application",
  initialState: {
    gameState: null,
    shouldRerender: true,
    gameObjectDetails: null,
    hoveredUnit: null,
  } as {
    gameState: GameState | null;
    shouldRerender: boolean;
    gameObjectDetails: GameObjectDetails | null;
    hoveredUnit: Unit | null;
  },
  reducers: {
    receiveGameState: (state, action: PayloadAction<GameState>) => {
      state.gameState = action.payload;
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
  },
});

export const {
  receiveGameState,
  renderedGameState,
  receivedGameObjectDetails,
  hoverUnit,
} = counterSlice.actions;

export const store = configureStore({
  reducer: counterSlice.reducer,
});

export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
