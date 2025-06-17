import { RefObject, useEffect, useRef } from "react";
import { useAppSelector } from "../state/hooks.ts";

const LogList = ({ logLines }: { logLines: string[] }) => {
  const myRef: RefObject<HTMLDivElement | null> = useRef(null);
  useEffect(() => {
    if (myRef.current) {
      myRef.current.scrollTop = myRef.current.scrollHeight;
    }
  });
  return (
    <div className="info-window" id="event-log" ref={myRef}>
      {logLines.map((log) => (
        <p>{log}</p>
      ))}
    </div>
  );
};

export const HUD = () => {
  const applicationState = useAppSelector((state) => state);

  return (
    <div>
      <div className={"sidebar sidebar-left"}>
        {applicationState.gameState ? (
          <LogList logLines={applicationState.gameState.eventLog} />
        ) : null}

        <div className="info-window" id="decision-description">
          {JSON.stringify(applicationState?.gameState?.decision, null, 4)}
        </div>
      </div>

      <div className={"sidebar sidebar-right"}>
        <h1>
          {applicationState.hoveredUnit
            ? applicationState.hoveredUnit.blueprint
            : "idk"}
        </h1>
      </div>
    </div>
  );
};
