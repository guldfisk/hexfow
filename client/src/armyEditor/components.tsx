import { useArmyEditorDispatch, useArmyEditorState } from "./state/hooks.ts";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";
import { addUnit, hoverUnit, removeUnit, setUnits } from "./state/store.ts";
import { UnitDetailsView } from "../components/unitDetails.tsx";
import { DetailsIndicator } from "../details/components.tsx";
import React from "react";
import { getAdditionalDetails } from "../details/additional.ts";
import { sortBlueprints, UnitList } from "../components/unitList.tsx";

const DetailsView = ({
  gameObjectDetails,
}: {
  gameObjectDetails: GameObjectDetails | null;
}) => {
  const detailed = useArmyEditorState((state) => state.detailed);
  const additionalDetailsIndex = useArmyEditorState(
    (state) => state.additionalDetailsIndex,
  );

  if (!gameObjectDetails || !detailed) {
    return <div className={"sidebar sidebar-right"}></div>;
  }

  return (
    <>
      {gameObjectDetails && additionalDetailsIndex !== null ? (
        <div className={"sidebar sidebar-details"}>
          <UnitDetailsView
            unit={null}
            details={
              gameObjectDetails.units[
                getAdditionalDetails(
                  { type: "blueprint", blueprint: detailed.identifier },
                  gameObjectDetails,
                )[additionalDetailsIndex].blueprint
              ]
            }
            gameObjectDetails={gameObjectDetails}
          />
        </div>
      ) : null}
      <div className={"sidebar sidebar-right"}>
        <UnitDetailsView
          unit={null}
          details={detailed}
          gameObjectDetails={gameObjectDetails}
        />
        {gameObjectDetails ? (
          <DetailsIndicator
            gameObjectDetails={gameObjectDetails}
            detail={{ type: "blueprint", blueprint: detailed.identifier }}
            additionalDetailsIndex={additionalDetailsIndex}
          />
        ) : null}
      </div>
    </>
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
                unit.price !== null &&
                unit.max_count > 0,
            )}
            onClick={(unit) => dispatch(addUnit(unit.identifier))}
            onHover={(unit) => dispatch(hoverUnit(unit))}
          />
        ) : null}
      </div>
      <div className={"main-content"}>
        {state.gameObjectDetails ? (
          <>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span>unit count: {state.armyList.length}</span>
              <span>
                army value:{" "}
                {state.armyList
                  .map((u) => state.gameObjectDetails?.units[u].price || 0)
                  .reduce((a, b) => a + b, 0)}{" "}
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
                  .sort(sortBlueprints)}
                onClick={(unit) => dispatch(removeUnit(unit.identifier))}
                onHover={(unit) => dispatch(hoverUnit(unit))}
              />
            </div>
          </>
        ) : null}
      </div>
      <DetailsView gameObjectDetails={state.gameObjectDetails} />
    </div>
  );
};
