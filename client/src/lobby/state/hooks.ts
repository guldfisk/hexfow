import { useDispatch, useSelector } from "react-redux";
import { LobbyDispatch, LobbyState } from "./store.ts";

export const useLobbyDispatch = useDispatch.withTypes<LobbyDispatch>();
export const useLobbyState = useSelector.withTypes<LobbyState>();
