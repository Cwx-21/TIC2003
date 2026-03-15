export const parsePositiveInt = (value) => {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
};

export const parseLimit = (value, defaultValue = 50, maxValue = 200) => {
  const parsed = parsePositiveInt(value);
  if (!parsed) {
    return defaultValue;
  }
  return Math.min(parsed, maxValue);
};

export const parseString = (value) => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
};
