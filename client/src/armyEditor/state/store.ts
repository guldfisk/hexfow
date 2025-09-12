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
import { getAdditionalDetails } from "../../details/additional.ts";

const mainSlice = createSlice({
  name: "armyEditor",
  initialState: {
    gameObjectDetails: null,
    detailed: null,
    additionalDetailsIndex: null,
    armyList: [],
  } as {
    gameObjectDetails: GameObjectDetails | null;
    detailed: UnitDetails | null;
    additionalDetailsIndex: number | null;
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
      state.additionalDetailsIndex = null;
    },
    incrementAdditionalDetailsIndex: (state) => {
      if (state.gameObjectDetails && state.detailed) {
        const amount = getAdditionalDetails(
          { type: "blueprint", blueprint: state.detailed.identifier },
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
  },
});

export const {
  receivedGameObjectDetails,
  hoverUnit,
  incrementAdditionalDetailsIndex,
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
