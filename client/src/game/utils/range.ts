export const mod = (a: number, b: number): number => ((a % b) + b) % b;

export const range = (
  first: number,
  second: number | undefined = undefined,
): number[] =>
  second == undefined
    ? [...Array(first).keys()]
    : [...Array(-first + second).keys()].map((v) => v + first);
