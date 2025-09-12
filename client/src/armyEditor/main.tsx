import "../../common.css";
import "./style.css";

import {incrementAdditionalDetailsIndex, receivedGameObjectDetails, store} from "./state/store.ts";
import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { Provider } from "react-redux";
import { GameObjectDetails } from "../interfaces/gameObjectDetails.ts";
import { ArmyEditor } from "./components.tsx";

fetch(
  `${window.location.protocol + "//" + window.location.hostname}:8000/game-object-details`,
).then(async (response) => {
  let jsonResponse: GameObjectDetails = await response.json();

  store.dispatch(receivedGameObjectDetails(jsonResponse));
});

const keyHandler = (event: KeyboardEvent) => {
  if (event.key == "d") {
    store.dispatch(incrementAdditionalDetailsIndex());
  }
};

document.addEventListener("keydown", keyHandler);

createRoot(document.getElementById("hud")!).render(
  <StrictMode>
    <Provider store={store}>
      <ArmyEditor />
    </Provider>
  </StrictMode>,
);
