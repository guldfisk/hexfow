export const min = <T>(items: T[], evaluator: (item: T) => number): T => {
  let best = items[0];
  let bestValue = null;

  for (const item of items) {
    const value = evaluator(item);
    if (bestValue === null || value < bestValue) {
      best = item;
      bestValue = value;
    }
  }
  return best;
};
