import { useMapEditorState } from "./state/hooks.ts";
import {setSelectedStatusIdentifier, setSelectedUnitIdentifier, store} from "./state/store.ts";

export const HUD = ({}: {}) => {
  const state = useMapEditorState((state) => state);

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {state.gameObjectDetails ? (
          <>
            <div className={"unit-list"}>
              {Object.values(state.gameObjectDetails.units).map((unit) => (
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
              ))}
            </div>
            <div className={"statuses-list"}>
              {Object.values(state.gameObjectDetails.statuses)
                .filter((status) => status.category == "hex")
                .map((status) => (
                  <h1
                    style={{
                      color:
                        state.selectedStatusIdentifier == status.identifier
                          ? "red"
                          : "white",
                    }}
                    onClick={() =>
                      store.dispatch(
                        setSelectedStatusIdentifier(status.identifier),
                      )
                    }
                  >
                    {status.name}
                  </h1>
                ))}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};
