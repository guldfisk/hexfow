import { configureStore, createSlice, PayloadAction } from "@reduxjs/toolkit";

export type GameType = "random" | "map";
export interface Seat {
  id: string;
  position: number;
  player_name: string;
}
export interface GameResponse {
  seats: Seat[];
}

export const getDefaultSettings = (state: LobbyState) => {
  if (state.selectedGameType == "map") {
    return { map_name: state.mapNames.length > 0 ? state.mapNames[0] : null };
  }
  return {};
};

const mainSlice = createSlice({
  name: "lobby",
  initialState: {
    selectedGameType: "map",
    gameResponse: null,
    withFow: true,
    withCustomArmies: true,
    settings: {},
    mapNames: [],
  } as {
    selectedGameType: GameType;
    gameResponse: GameResponse | null;
    settings: { [key: string]: any };
    withFow: boolean;
    withCustomArmies: boolean,
    mapNames: string[];
  },
  reducers: {
    setSelectedGameType: (state, action: PayloadAction<GameType>) => {
      state.selectedGameType = action.payload;
      state.settings = getDefaultSettings(state);
    },
    setWithFow: (state, action: PayloadAction<boolean>) => {
      state.withFow = action.payload;
    },
    setWithCustomArmies: (state, action: PayloadAction<boolean>) => {
      state.withCustomArmies = action.payload;
    },
    setGameResponse: (state, action: PayloadAction<GameResponse>) => {
      state.gameResponse = action.payload;
    },
    setSettings: (state, action: PayloadAction<{ [key: string]: any }>) => {
      state.settings = action.payload;
    },
    setMapNames: (state, action: PayloadAction<string[]>) => {
      state.mapNames = action.payload;
      state.settings = getDefaultSettings(state);
    },
  },
});

export const {
  setSelectedGameType,
  setSettings,
  setWithFow,
  setWithCustomArmies,
  setGameResponse,
  setMapNames,
} = mainSlice.actions;

export const store = configureStore({
  reducer: mainSlice.reducer,
  // middleware: () => new Tuple(),
});

export type LobbyState = ReturnType<typeof store.getState>;
export type LobbyDispatch = typeof store.dispatch;
