export interface MapAnimation {
  play: (elapsed: number) => boolean;
}

const getTriangleWave = (period: number): ((t: number) => number) => {
  return (t: number) =>
    (4 / period) *
    (t - (period / 2) * Math.floor((2 * t) / period + 0.5)) *
    (-1) ** Math.floor((2 * t) / period + 0.5);
};

export const linear = (cursor: number) => cursor;

export const sigmoid = (cursor: number) =>
  cursor >= 1 ? 1 : 1 / (1 + Math.exp(-7 * (cursor - 0.5)));

export const shake = (cursor: number) => getTriangleWave(1)(cursor * 2);

export const makeAnimation = (
  play: (cursor: number) => void,
  duration: number,
  path: (cursor: number) => number,
  onFinished: (() => void) | null = null,
): MapAnimation => {
  return {
    play: (elapsed: number): boolean => {
      play(path(Math.min(elapsed / duration, 1)));
      if (elapsed >= duration) {
        if (onFinished) {
          onFinished();
        }
        return false;
      }
      return true;
    },
  };
};
