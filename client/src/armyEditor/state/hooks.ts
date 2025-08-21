import { useDispatch, useSelector } from "react-redux";
import { ArmyEditorDispatch, ArmyEditorState } from "./store.ts";

export const useArmyEditorDispatch = useDispatch.withTypes<ArmyEditorDispatch>();
export const useArmyEditorState = useSelector.withTypes<ArmyEditorState>();
