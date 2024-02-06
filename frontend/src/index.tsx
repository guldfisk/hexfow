import React from "react";
import { createRoot } from "react-dom/client";
import {App} from "./app";

const container = document.getElementById("app");
const root = createRoot(container);
root.render(
  <div
      // style={{margin: 0, padding: 0, overflow: 'hidden'}}
  >
    {/*<h1>LMAO</h1>*/}
    <App />
  </div>,
);
