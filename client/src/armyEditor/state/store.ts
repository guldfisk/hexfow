import {
  configureStore,
  createSlice,
  PayloadAction,
  Tuple,
} from "@reduxjs/toolkit";
import {
  GameObjectDetails,
  UnitDetails,
} from "../../interfaces/gameObjectDetails.ts";

const mainSlice = createSlice({
  name: "armyEditor",
  initialState: {
    gameObjectDetails: null,
    detailed: null,
    armyList: [],
  } as {
    gameObjectDetails: GameObjectDetails | null;
    detailed: UnitDetails | null;
    armyList: string[];
  },
  reducers: {
    receivedGameObjectDetails: (
      state,
      action: PayloadAction<GameObjectDetails>,
    ) => {
      state.gameObjectDetails = action.payload;
    },
    setUnits: (state, action: PayloadAction<string[]>) => {
      state.armyList = action.payload;
    },
    addUnit: (state, action: PayloadAction<string>) => {
      if (!state.armyList.includes(action.payload)) {
        state.armyList = state.armyList.concat(action.payload);
      }
    },
    removeUnit: (state, action: PayloadAction<string>) => {
      state.armyList = state.armyList.filter((v) => v != action.payload);
    },
    hoverUnit: (state, action: PayloadAction<UnitDetails>) => {
      state.detailed = action.payload;
    },
  },
});

export const {
  receivedGameObjectDetails,
  hoverUnit,
  setUnits,
  addUnit,
  removeUnit,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  middleware: () => new Tuple(),
});

export type ArmyEditorState = ReturnType<typeof store.getState>;
export type ArmyEditorDispatch = typeof store.dispatch;
