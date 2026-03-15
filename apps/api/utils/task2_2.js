import sequelize, { hasDbConfig } from "../database/index.js";

export const getDbOrError = (res) => {
  if (!hasDbConfig || !sequelize) {
    res.status(500).json({ error: "DATABASE_URL is not configured" });
    return null;
  }
  return sequelize;
};

export const normalizeSymbol = (value) => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim().toUpperCase();
  return trimmed.length ? trimmed : null;
};

export const parseBoolean = (value) => {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (["true", "1", "yes"].includes(normalized)) {
    return true;
  }
  if (["false", "0", "no"].includes(normalized)) {
    return false;
  }
  return null;
};
