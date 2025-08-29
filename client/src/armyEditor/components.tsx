import { useArmyEditorDispatch, useArmyEditorState } from "./state/hooks.ts";
import {
  GameObjectDetails,
  UnitDetails,
} from "../interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../image/images.ts";
import { addUnit, hoverUnit, removeUnit, setUnits } from "./state/store.ts";
import { UnitDetailsView } from "../components/unitDetails.tsx";

const UnitListItem = ({
  unit,
  onClick,
}: {
  unit: UnitDetails;
  onClick: ((unit: UnitDetails) => void) | null;
}) => {
  const dispatch = useArmyEditorDispatch();

  return (
    <div
      className={"unit-list-item"}
      onMouseEnter={() => dispatch(hoverUnit(unit))}
      onClick={() => (onClick ? onClick(unit) : null)}
    >
      <span>{`${unit.name} - ${unit.price}`}</span>
      <img
        src={getImageUrl("unit", unit.identifier)}
        className={"unit-thumbnail"}
      />
    </div>
  );
};

const UnitList = ({
  units,
  onClick,
}: {
  units: UnitDetails[];
  onClick: ((unit: UnitDetails) => void) | null;
}) => {
  return (
    <div className={"unit-list"}>
      {units.map((unit) => (
        <UnitListItem unit={unit} onClick={onClick} />
      ))}
    </div>
  );
};

const DetailsView = ({
  gameObjectDetails,
}: {
  gameObjectDetails: GameObjectDetails | null;
}) => {
  const detailed = useArmyEditorState((state) => state.detailed);

  return (
    <div className={"sidebar sidebar-right"}>
      {gameObjectDetails && detailed ? (
        <UnitDetailsView
          unit={null}
          details={detailed}
          gameObjectDetails={gameObjectDetails}
        />
      ) : null}
    </div>
  );
};

const saveArmyList = (unitNames: string[]) => {
  const blob = new Blob([unitNames.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "army_list.txt";
  a.click();
};

export const ArmyEditor = ({}: {}) => {
  const state = useArmyEditorState((state) => state);
  const dispatch = useArmyEditorDispatch();
  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {state.gameObjectDetails ? (
          <UnitList
            units={Object.values(state.gameObjectDetails.units).filter(
              (unit) =>
                !state.armyList.includes(unit.identifier) &&
                unit.price !== null,
            )}
            onClick={(unit) => dispatch(addUnit(unit.identifier))}
          />
        ) : null}
      </div>
      <div className={"main-content"}>
        {state.gameObjectDetails ? (
          <>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span>unit count: {state.armyList.length} / 12</span>
              <span>
                army value:{" "}
                {state.armyList
                  .map((u) => state.gameObjectDetails?.units[u].price)
                  .reduce((a, b) => a + b, 0)}{" "}
                / 70
              </span>
              <button onClick={() => saveArmyList(state.armyList)}>
                export
              </button>
              <div>
                <label>load</label>
                <input
                  type="file"
                  id="fileInput"
                  onChange={(event) => {
                    let fr = new FileReader();

                    fr.onload = () =>
                      dispatch(
                        setUnits(
                          (fr.result as string)
                            .split("\n")
                            .filter(
                              (id) => id in state.gameObjectDetails?.units,
                            ),
                        ),
                      );

                    fr.readAsText(event.target.files[0]);
                  }}
                />
              </div>
            </div>
            <div className={"army-list"}>
              <UnitList
                units={Object.values(state.gameObjectDetails.units)
                  .filter((unit) => state.armyList.includes(unit.identifier))
                  .sort((a, b) => {
                    if (a.price > b.price) {
                      return 1;
                    }
                    if (b.price > a.price) {
                      return -1;
                    }
                    if (a.identifier > b.identifier) {
                      return 1;
                    }
                    if (b.identifier > b.identifier) {
                      return -1;
                    }
                    return 0;
                  })}
                onClick={(unit) => dispatch(removeUnit(unit.identifier))}
              />
            </div>
          </>
        ) : null}
      </div>
      <DetailsView gameObjectDetails={state.gameObjectDetails} />
    </div>
  );
};
