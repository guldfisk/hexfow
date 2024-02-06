import React, { PropsWithChildren } from "react";
import * as PIXI from "pixi.js";

import { PixiComponent, useApp } from "@pixi/react";
import { Viewport } from "pixi-viewport";
import { Application as PixiApplication } from "@pixi/app";
import { forwardRef } from "react";

const WORLD_WIDTH = 2000;
const WORLD_HEIGHT = 2000;

const PixiViewportComponent = PixiComponent("Viewport", {
  create(props: { app: PixiApplication; [p: string]: any }) {
    const { app, ...viewportProps } = props;

    // create(props) {
    //   const { app, ...viewportProps } = props;
    //   const app = useApp()

    // Install EventSystem, if not already
    // (PixiJS 6 doesn't add it by default)
    if (!("events" in app.renderer))
      // @ts-ignore
      app.renderer.addSystem(PIXI.EventSystem, "events");

    const viewport = new Viewport({
      worldWidth: WORLD_WIDTH,
      worldHeight: WORLD_HEIGHT,
      // passiveWheel: false,
      events: app.renderer.events,
        disableOnContextMenu: true,
    });

    viewport.drag({mouseButtons: 'right'}).wheel({});

    return viewport;
  },
  // applyProps(viewport, _oldProps, _newProps) {
  //   const { plugins: oldPlugins, children: oldChildren, ...oldProps } = _oldProps;
  //   const { plugins: newPlugins, children: newChildren, ...newProps } = _newProps;
  //
  //   Object.keys(newProps).forEach((p) => {
  //     if (oldProps[p] !== newProps[p]) {
  //       // @ts-ignore
  //         viewport[p] = newProps[p];
  //     }
  //   });
  // },
  didMount() {
    console.log("viewport mounted");
  },
});

export const PixiViewport = (props: PropsWithChildren) => (
  <PixiViewportComponent app={useApp()}>{props.children}</PixiViewportComponent>
);
// const PixiViewport = forwardRef((props, ref) => (
//   <PixiViewportComponent ref={ref} app={useApp()} {...props} />
// ));
