import camelcase from "camelcase";

export const recursiveCamelCase = <Type>(obj: Type): Type => {
  if (!obj) {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(recursiveCamelCase);
  }
  if (typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [camelcase(k), recursiveCamelCase(v)]),
    );
  }
  return obj;
};
