import { _ReactPixi, Container, Graphics, Sprite, useTick } from "@pixi/react";
import React, { useCallback, useRef, useState } from "react";
import { Graphics as PIXIGraphics } from "pixi.js";
import { HexData, MapData } from "../models/map";
import { HexCoord } from "../models/types";

const cardWidth = 140;
const cardHeight = 200;

const hexSize = 170;

// const hexWidth = hexSize * 2;
// const hexHeight = Math.sqrt(3) * hexSize;

const hexWidth = Math.sqrt(3) * hexSize;
const hexHeight = hexSize * 2;

// const hexVerts: [number, number][] = [
//   [hexSize, 0],
//   [hexSize / 2, -hexHeight / 2],
//   [-hexSize / 2, -hexHeight / 2],
//   [-hexSize, 0],
//   [-hexSize / 2, hexHeight / 2],
//   [hexSize / 2, hexHeight / 2],
// ];

const hexVerts: [number, number][] = [
  [hexWidth / 2, -hexSize / 2],
  [0, -hexSize],
  [-hexWidth / 2, -hexSize / 2],
  [-hexWidth / 2, hexSize / 2],
  [0, hexHeight / 2],
  [hexWidth / 2, hexSize / 2],
];

//
// const addHex = (position: [number, number], color: number) => {
//   let container = new PIXI.Container();
//   // container.position.set(app.view.width / 2, app.view.height / 2)
//   container.position.set(...position);
//   app.stage.addChild(container);
//   let obj = new PIXI.Graphics();
//   obj.beginFill(color);
//   obj.lineStyle({ alignment: 0, color: 0x222222, width: 3 });
//   obj.moveTo(...hexVerts[0]);
//
//   // hexVerts.slice(1).forEach((vert) => obj.lineTo(...vert));
//   hexVerts.slice(1).forEach((vert) => drawDashLine(obj, ...vert));
//   obj.closePath();
//   container.addChild(obj);
//
//   obj.eventMode = "static";
//   obj.on("pointerdown", () =>
//     container.position.set(
//       container.position.x + hexWidth,
//       container.position.y,
//     ),
//   );
// };

const vectorLength = (x: number, y: number) =>
  Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2));

const drawDashLine = (
  obj: PIXIGraphics,
  x: number,
  y: number,
  dash = 13,
  gap = 2,
  offset: number = 0,
): number => {
  const [fromX, fromY] = obj.currentPath.points.slice(-2);
  const length = vectorLength(x - fromX, y - fromY);

  let solid = Math.floor(offset / dash) % 2 == 1 || offset == 0;
  let position = 0;
  let leftover = 0;

  while (position < length) {
    if (offset > 0) {
      position = offset % dash;
      offset = 0;
    } else {
      position = position + dash;
      if (position > length) {
        leftover = length - position;
        position = length;
      }
    }

    (solid ? obj.lineTo : obj.moveTo).bind(obj)(
      fromX + (position / length) * (x - fromX),
      fromY + (position / length) * (y - fromY),
    );
    solid = !solid;
  }

  obj.moveTo(x, y);
  return -leftover + (solid ? 0 : dash);
};

const drawDashedShape = (
  obj: PIXIGraphics,
  shape: [number, number][],
  dash: number = 13,
  gap: number = 2,
  offset: number = 0,
) => {
  obj.moveTo(...shape[0]);
  let currentOffset = offset;
  shape
    .slice(1)
    .concat([hexVerts[0]])
    .forEach((vert) => {
      currentOffset = drawDashLine(obj, ...vert, dash, gap, currentOffset);
    });
};

// const hexToPixelCoord = (hexCoord: HexCoord): [number, number] => [
//   hexSize * ((3 / 2) * hexCoord.r),
//   hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
// ];

const hexToPixelCoord = (hexCoord: HexCoord): [number, number] => [
  hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  hexSize * ((3 / 2) * hexCoord.r),
];

const rasterizeColor = (r: number, g: number, b: number) =>
  Math.floor(r * 255) * 0x010000 +
  Math.floor(g * 255) * 0x00100 +
  Math.floor(b * 255);

let zindex = 10;

export const Hex = (props: { coord: HexCoord; hexData: HexData }) => {
  const [shade, setShade] = useState(0);
  const [selected, setSelected] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [shake, setShake] = useState(0);
  const [localZ, setLocalZ] = useState(1);

  const mask = useRef();

  useTick((delta) => {
    setShade(shade + delta);
    if (shake > 0) {
      setShake((shake) => Math.max(shake - delta / 5, 0));
    }
  });

  const draw = useCallback(
    (g: PIXIGraphics) => {
      g.clear();
      // g.beginFill(selected ? 0x00ff33 : 0xff3300);
      g.beginFill(rasterizeColor(0.7 + (shake / 9) * 0.2, 0.5, 0.6));
      // g.beginFill(rasterizeColor(Math.abs(Math.sin(shade)), Math.abs(Math.cos(shade)), 0));
      g.lineStyle({ alignment: 0, color: 0x222222, width: 3 });
      g.moveTo(...hexVerts[0]);
      hexVerts.slice(1).forEach((vert) => g.lineTo(...vert));
      // hexVerts.slice(1).forEach((vert) => drawDashLine(g, ...vert));
      g.closePath();
    },
    [shake],
  );

  // const mask = new PIXIGraphics();
  // mask.beginFill();
  // mask.moveTo(...hexVerts[0]);
  // hexVerts.slice(1).forEach((vert) => mask.lineTo(...vert));
  // mask.closePath();

  const dotted = useCallback(
    (g: PIXIGraphics) => {
      g.clear();
      g.lineStyle({ alignment: 0, color: 0xb6c0d1, width: 3 });

      // g.moveTo(...hexVerts[0]);
      // drawDashLine(g, ...hexVerts[1], 13, 2, Math.floor(shade * 13));

      // drawDashedShape(g, hexVerts.slice(0, 5))

      drawDashedShape(g, hexVerts, 13, 2, Math.floor((shade / 50) * 13));
      // drawDashedShape(g, hexVerts, 13, 2, 5);

      // g.moveTo(...hexVerts[0]);
      // hexVerts
      //   .slice(1)
      //   .concat([hexVerts[0]])
      //   .forEach((vert) => drawDashLine(g, ...vert));
      // g.closePath();
    },
    [shade],
  );

  const rectangle = useCallback((g: PIXIGraphics) => {
    g.clear();
    g.beginFill(0xffffff);
    g.drawRect(-cardWidth / 2, -cardHeight / 2, cardWidth, cardHeight);
  }, []);
  return (
    <Container
      position={hexToPixelCoord(props.coord)}
      click={(event) => {
        setSelected((prevState) => !prevState);
        console.log(event.buttons);
      }}
      rotation={Math.sin(shake > 0 ? shake - 3 : 0) / 10}
      scale={1 + 0.3 * (shake / 9)}
      zIndex={localZ}
      onmouseenter={() => {
        setHovered(true);
        setShake(9);
        zindex += 1;
        setLocalZ(zindex);
        console.log(zindex);
      }}
      onmouseleave={() => setHovered(false)}
      eventMode={"static"}
    >
      <Graphics draw={draw} ref={mask}></Graphics>
      {/*<Container>*/}
      {/*  <Sprite*/}
      {/*    // mask={mask.current}*/}
      {/*    image={`/static/${props.hexData.terrainType}.png`}*/}
      {/*    anchor={0.5}*/}
      {/*  />*/}
      {/*</Container>*/}
      {hovered && <Graphics draw={dotted}></Graphics>}
      {/*<Graphics draw={rectangle} angle={selected ? 90 : 0}></Graphics>*/}
    </Container>
  );
};

// const f = ({v}: {v: number}) => {v.toFixed()}

export const HexMap = (props: {
  containerProps: React.PropsWithChildren<_ReactPixi.IContainer>;
  mapData: MapData;
}) => {
  const [rotation, setRotation] = useState(0);

  const mask = useRef();

  useTick((delta) => {
    setRotation(rotation + delta);
  });
  // export const HexMap = (props: {containerProps: React.PropsWithChildren}) => {
  // export const HexMap = (props: {containerProps: number}) => {
  return (
    <Container
      {...props.containerProps}
      sortableChildren={true}
      // rotation={rotation / -150}
    >
      {Array.from(props.mapData.entries()).map(([key, value]) => (
        <Hex coord={key} hexData={value} />
      ))}
      {/*<Hex coord={{ h: 0, r: 0 }}></Hex>*/}
      {/*<Hex coord={{ h: 1, r: 0 }}></Hex>*/}
      {/*<Hex coord={{ h: 0, r: 1 }}></Hex>*/}
      {/*<Hex coord={{ h: 1, r: 1 }}></Hex>*/}
      {/*<Hex coord={{ h: -1, r: 0 }}></Hex>*/}
      {/*<Hex coord={{ h: -2, r: 0 }}></Hex>*/}
    </Container>
  );
};
