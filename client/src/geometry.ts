import { CC, RC } from "./interfaces/geometry.ts";
import { mod, range } from "./utils/range.ts";

export const hexSize = 160;

export const getHexDimensions = (size: number) => [
  Math.sqrt(3) * size,
  size * 2,
];

export const [hexWidth, hexHeight] = getHexDimensions(hexSize);

export const getHexVerticeOffsets = (hexSize: number): [number, number][] => {
  const [hexWidth, hexHeight] = getHexDimensions(hexSize);
  return [
    [hexWidth / 2, -hexSize / 2],
    [0, -hexSize],
    [-hexWidth / 2, -hexSize / 2],
    [-hexWidth / 2, hexSize / 2],
    [0, hexHeight / 2],
    [hexWidth / 2, hexSize / 2],
  ];
};

export const hexVerticeOffsets = getHexVerticeOffsets(hexSize);

export const ccNeighborOffsets: CC[] = [
  { r: 1, h: 0 },
  { r: 1, h: -1 },
  { r: 0, h: -1 },
  { r: -1, h: 0 },
  { r: -1, h: 1 },
  { r: 0, h: 1 },
];

export const getL = (cc: CC): number => -(cc.r + cc.h);

export const roundCC = (cc: CC): CC => {
  let r = Math.round(cc.r);
  let h = Math.round(cc.h);
  let l = Math.round(getL(cc));
  const rDiff = Math.abs(cc.r - r);
  const hDiff = Math.abs(cc.h - h);
  const lDiff = Math.abs(getL(cc) - l);

  if (rDiff > hDiff && rDiff > lDiff) {
    r = -h - l;
  } else if (hDiff > lDiff) {
    h = -r - l;
  }

  return { r, h };
};

export const rcToCC = (rc: RC): CC => {
  const x = rc.x / hexSize;
  const y = rc.y / hexSize;
  return roundCC({ r: (2 / 3) * y, h: (Math.sqrt(3) / 3) * x - (1 / 3) * y });
};

export const ccToRC = (hexCoord: CC): RC => ({
  x: hexSize * ((Math.sqrt(3) / 2) * hexCoord.r + Math.sqrt(3) * hexCoord.h),
  y: hexSize * ((3 / 2) * hexCoord.r),
});

export const ccToKey = (cc: CC): string => `${cc.r},${cc.h}`;

export const ccFromKey = (key: string): CC => {
  const [r, h] = key.split(",");
  return { r: parseInt(r), h: parseInt(h) };
};

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

export const ccEquals = (a: CC, b: CC): boolean => a.r == b.r && a.h == b.h;

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

export const hexRing = (radius: number, center: CC | null = null): CC[] => {
  const result = [];
  for (const i of range(radius + 1)) {
    result.push({ r: -radius, h: i });
  }
  for (const i of range(-radius + 1, 1)) {
    result.push({ r: i, h: radius });
  }
  for (const i of range(radius - 1)) {
    result.push({ r: i + 1, h: radius - 1 - i });
  }
  for (const i of range(-radius, 1).reverse()) {
    result.push({ r: radius, h: i });
  }
  for (const i of range(radius).reverse()) {
    result.push({ r: i, h: -radius });
  }
  for (const i of range(radius - 1)) {
    result.push({ r: -(i + 1), h: -(radius - 1 - i) });
  }
  return center ? result.map((cc) => addCCs(cc, center)) : result;
};

export const hexArc = (
  radius: number,
  armLength: number,
  strokeCenter: CC,
  arcCenter: CC | null = null,
): CC[] => {
  const ring = hexRing(radius, arcCenter);
  for (const [idx, cc] of ring.entries()) {
    if (ccEquals(cc, strokeCenter)) {
      return range(-armLength, armLength + 1).map(
        (offset) => ring[mod(idx + offset, ring.length)],
      );
    }
  }
  throw new Error("invalid stroke center");
};
