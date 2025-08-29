import { useMapEditorDispatch, useMapEditorState } from "./state/hooks.ts";
import {
  loadMap,
  setLoaderOptions,
  setLoaderSelected,
  setMapName,
  setSelectedStatusIdentifier,
  setSelectedUnitIdentifier,
  setShowLoader,
  store,
} from "./state/store.ts";
import { useEffect } from "react";

const NameEditor = ({}) => {
  const mapName = useMapEditorState((state) => state.mapName);
  const dispatch = useMapEditorDispatch();
  return (
    <input
      type={"text"}
      value={mapName}
      onChange={(event) => dispatch(setMapName(event.target.value))}
    />
  );
};

const MapLoader = ({}) => {
  const loaderState = useMapEditorState((state) => state.loaderData);
  const dispatch = useMapEditorDispatch();

  useEffect(() => {
    fetch(
      `${window.location.protocol + "//" + window.location.hostname}:8000/maps`,
    ).then(async (response) => {
      const names = (await response.json()).map((map) => map.name);
      dispatch(setLoaderOptions(names));
      dispatch(setLoaderSelected(names[0]));
    });
    return () => {};
  }, []);

  return (
    <div
      className={
        loaderState.show ? "modal display-block" : "modal display-none"
      }
    >
      <div className={"modal-main"}>
        <select
          value={loaderState.selected}
          onChange={(event) => dispatch(setLoaderSelected(event.target.value))}
        >
          {loaderState.options.map((name) => (
            <option value={name}>{name}</option>
          ))}
        </select>
        <button
          onClick={() =>
            fetch(
              `${window.location.protocol + "//" + window.location.hostname}:8000/maps/${loaderState.selected}`,
            ).then(async (response) => {
              dispatch(loadMap(await response.json()));
            })
          }
        >
          load
        </button>
        <button onClick={() => dispatch(setShowLoader(false))}>cancel</button>
      </div>
    </div>
  );
};

export const HUD = ({}: {}) => {
  const state = useMapEditorState((state) => state);
  const dispatch = useMapEditorDispatch();
  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        <NameEditor />
        <button
          onClick={() =>
            fetch(
              `${window.location.protocol + "//" + window.location.hostname}:8000/maps`,
              {
                method: "POST",
                body: JSON.stringify({
                  name: state.mapName,
                  scenario: {
                    hexes: Object.values(state.mapData).map((spec) => ({
                      cc: spec.cc,
                      terrain_type: spec.terrainType,
                      is_objective: spec.isObjective,
                      deployment_zone_of: spec.deploymentZoneOf === undefined ? null : spec.deploymentZoneOf,
                      statuses: spec.statuses,
                      unit: spec.unit || null,
                    })),
                  },
                }),
                headers: {
                  "Content-type": "application/json",
                },
              },
            )
          }
        >
          save
        </button>
        <button onClick={() => dispatch(setShowLoader(true))}>load map</button>
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
      <MapLoader />
    </div>
  );
};
