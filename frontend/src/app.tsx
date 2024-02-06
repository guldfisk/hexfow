import React from "react";
import { Stage } from "@pixi/react";
import { HexMap } from "./hexes/hexmap";
import { PixiViewport } from "./viewport";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { deserializeMap, HexData, MapData } from "./models/map";

const websocketUrl = "ws://localhost:9000/ws/chat/";
const connectionStatusMap = {
  [ReadyState.CONNECTING]: "Connecting",
  [ReadyState.OPEN]: "Open",
  [ReadyState.CLOSING]: "Closing",
  [ReadyState.CLOSED]: "Closed",
  [ReadyState.UNINSTANTIATED]: "Uninstantiated",
};

export const App = () => {
  const { sendMessage, lastMessage, readyState } = useWebSocket(websocketUrl);
  const hexMap: MapData | null =
    lastMessage == null ? null : deserializeMap(JSON.parse(lastMessage.data));
  return (
    <>
      <Stage
        // onClick={(event) => console.log(event.type, event.buttons)}
        // onMouseDown={(event) => console.log(event.type, event.buttons)}
        width={window.innerWidth}
        height={window.innerHeight}
        //   width={}
        style={{ position: "absolute" }}
        options={{ antialias: true }}
      >
        <PixiViewport>
          {hexMap && (
            <HexMap mapData={hexMap} containerProps={{ x: 400, y: 400 }} />
          )}
          {/*<HexMap containerProps={{ x: 400, y: 400 }}></HexMap>*/}
        </PixiViewport>
      </Stage>
      <div
        style={{
          position: "fixed",
          top: 10,
          left: 10,
          width: "20%",
          bottom: 10,
          background: "gray",
        }}
      >
        <span>
          The WebSocket is currently {connectionStatusMap[readyState]}
        </span>
      </div>
    </>
  );
};
