import { useDispatch, useSelector } from "react-redux";
import { MapEditorDispatch, MapEditorState } from "./store.ts";

export const useMapEditorDispatch = useDispatch.withTypes<MapEditorDispatch>();
export const useMapEditorState = useSelector.withTypes<MapEditorState>();
