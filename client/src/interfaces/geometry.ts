export interface RC {
  x: number;
  y: number;
}

export interface CC {
  r: number;
  h: number;
}

export type CornerPosition = 0 | 1;

export interface Corner {
  cc: CC;
  position: CornerPosition;
}
