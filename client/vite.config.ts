import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  esbuild: {
    supported: {
      "top-level-await": true, //browsers can handle top-level-await features
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        play: "./play/index.html",
        "map-editor": "./map-editor/index.html",
        "army-editor": "./army-editor/index.html",
      },
    },
  },
});
