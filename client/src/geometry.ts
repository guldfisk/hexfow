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

export const ccNeighborOffsets: CC[] = [
  { r: 1, h: 0 },
  { r: 1, h: -1 },
  { r: 0, h: -1 },
  { r: -1, h: 0 },
  { r: -1, h: 1 },
  { r: 0, h: 1 },
];

export const ccToRC = (hexCoord: CC): RC => ({
  x: hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  y: hexSize * ((3 / 2) * hexCoord.r),
});

export const ccToKey = (cc: CC): string => `${cc.r},${cc.h}`;

export const addRCs = (a: RC, b: RC): RC => ({
  x: a.x + b.x,
  y: a.y + b.y,
});

export const addCCs = (a: CC, b: CC): CC => ({
  r: a.r + b.r,
  h: a.h + b.h,
});

export const subRCs = (a: RC, b: RC): RC => ({
  x: a.x - b.x,
  y: a.y - b.y,
});

export const subCCs = (a: CC, b: CC): CC => ({
  r: a.r - b.r,
  h: a.h - b.h,
});

export const ccDistance = (a: CC, b: CC): number => {
  const difference = subCCs(a, b);
  return (
    (Math.abs(difference.r) +
      Math.abs(difference.r + difference.h) +
      Math.abs(difference.h)) /
    2
  );
};

export const asUnitVector = (rc: RC) =>
  constDivRc(rc, Math.sqrt(rc.x ** 2 + rc.y ** 2));

export const constMultRC = (rc: RC, v: number) => ({
  x: rc.x * v,
  y: rc.y * v,
});
export const constMultCC = (cc: CC, v: number) => ({
  r: cc.r * v,
  h: cc.h * v,
});
export const constDivRc = (rc: RC, v: number) => ({ x: rc.x / v, y: rc.y / v });

export const hexDistance = (fromCC: CC, toCC: CC): number => {
  const r = fromCC.r - toCC.r;
  const h = fromCC.h - toCC.h;
  return (Math.abs(r) + Math.abs(r + h) + Math.abs(h)) / 2;
};

export const getNeighborsOffCC = (cc: CC): CC[] =>
  ccNeighborOffsets.map((offset) => addCCs(cc, offset));
