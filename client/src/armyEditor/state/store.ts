import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import { GameObjectDetails } from "../../game/interfaces/gameObjectDetails.ts";

const mainSlice = createSlice({
  name: "armyEditor",
  initialState: {
    gameObjectDetails: null,
    units: [],
  } as {
    gameObjectDetails: GameObjectDetails | null;
    units: string[];
  },
  reducers: {
    receivedGameObjectDetails: (
      state,
      action: PayloadAction<GameObjectDetails>,
    ) => {
      state.gameObjectDetails = action.payload;
    },
  },
});

export const { receivedGameObjectDetails } = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type ArmyEditorState = ReturnType<typeof store.getState>;
export type ArmyEditorDispatch = typeof store.dispatch;
