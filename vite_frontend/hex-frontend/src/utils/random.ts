export const randomChoice = <T>(values: T[]): T =>
  values[Math.floor(Math.random() * values.length)];
