import { useMapEditorState } from "./state/hooks.ts";
import { setSelectedUnitIdentifier, store } from "./state/store.ts";

export const HUD = ({}: {}) => {
  const state = useMapEditorState((state) => state);

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {state.gameObjectDetails
          ? Object.values(state.gameObjectDetails.units).map((unit) => (
              <h1
                style={{
                  color:
                    state.selectedUnitIdentifier == unit.identifier
                      ? "red"
                      : "white",
                }}
                onClick={() =>
                  store.dispatch(setSelectedUnitIdentifier(unit.identifier))
                }
              >
                {unit.name}
              </h1>
            ))
          : null}
      </div>
    </div>
  );
};
