import { CC, RC } from "./interfaces/geometry.ts";

export const hexSize = 160;

export const getHexDimensions = (size: number) => [
  Math.sqrt(3) * size,
  size * 2,
];

export const [hexWidth, hexHeight] = getHexDimensions(hexSize);

export const hexVerticeOffsets: [number, number][] = [
  [hexWidth / 2, -hexSize / 2],
  [0, -hexSize],
  [-hexWidth / 2, -hexSize / 2],
  [-hexWidth / 2, hexSize / 2],
  [0, hexHeight / 2],
  [hexWidth / 2, hexSize / 2],
];

export const CCToRC = (hexCoord: CC): RC => ({
  x: hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  y: hexSize * ((3 / 2) * hexCoord.r),
});

export const addRCs = (a: RC, b: RC): RC => ({
  x: a.x + b.x,
  y: a.y + b.y,
});

export const subRCs = (a: RC, b: RC): RC => ({
  x: a.x - b.x,
  y: a.y - b.y,
});

export const assUnitVector = (rc: RC) =>
  constDivRc(rc, Math.sqrt(rc.x ** 2 + rc.y ** 2));

export const constMultRC = (rc: RC, v: number) => ({
  x: rc.x * v,
  y: rc.y * v,
});
export const constDivRc = (rc: RC, v: number) => ({ x: rc.x / v, y: rc.y / v });

export const hexDistance = (fromCC: CC, toCC: CC): number => {
  const r = fromCC.r - toCC.r;
  const h = fromCC.h - toCC.h;
  return (Math.abs(r) + Math.abs(r + h) + Math.abs(h)) / 2;
};
