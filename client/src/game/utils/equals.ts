export const deepEquals = (a: any, b: any): boolean => {
  if (a === b) {
    return true;
  }

  if (a && b && typeof a === "object" && typeof b === "object") {
    const arrA = Array.isArray(a),
      arrB = Array.isArray(b);

    if (arrA && arrB) {
      if (a.length !== b.length) {
        return false;
      }
      for (let i = 0; i < a.length; i++) {
        if (!deepEquals(a[i], b[i])) {
          return false;
        }
      }
      return true;
    }

    if (arrA !== arrB) {
      return false;
    }

    const keys = Object.keys(a);

    if (keys.length !== Object.keys(b).length) {
      return false;
    }

    for (const key of keys) {
      if (!deepEquals(a[key], b[key])) {
        return false;
      }
    }

    return true;
  }

  return false;
}
