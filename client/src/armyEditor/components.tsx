import { useArmyEditorDispatch, useArmyEditorState } from "./state/hooks.ts";
import { UnitDetails } from "../game/interfaces/gameObjectDetails.ts";
import { getImageUrl } from "../game/images.ts";

const UnitListItem = ({ unit }: { unit: UnitDetails }) => (
  <div className={"unit-list-item"}>
    <span>{unit.name}</span>
    <span>{unit.price}</span>
    <img src={getImageUrl("unit", unit.identifier)} className={'unit-thumbnail'}/>
  </div>
);

const UnitList = ({ units }: { units: UnitDetails[] }) => {
  return (
    <div className={"unit-list"}>
      {units.map((unit) => (
        <UnitListItem unit={unit} />
        // <h1
        // // style={{
        // //   color:
        // //       state.selectedUnitIdentifier == unit.identifier
        // //           ? "red"
        // //           : "white",
        // // }}
        // >
        //   {unit.name}
        // </h1>
      ))}
    </div>
  );
};

export const ArmyEditor = ({}: {}) => {
  const state = useArmyEditorState((state) => state);
  const dispatch = useArmyEditorDispatch();
  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {state.gameObjectDetails ? (
          <UnitList units={Object.values(state.gameObjectDetails.units)} />
        ) : null}
      </div>
    </div>
  );
};
