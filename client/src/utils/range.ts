
export const range = (
  first: number,
  second: number | undefined = undefined,
): number[] =>
  second == undefined
    ? [...Array(first).keys()]
    : [...Array(-first + second).keys()].map((v) => v + first);