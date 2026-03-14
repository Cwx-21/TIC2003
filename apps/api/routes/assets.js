import express from "express";
import { QueryTypes } from "sequelize";
import { getDbOrError, parseBoolean } from "../utils/task2_2.js";
import { parseLimit, parseString } from "../utils/query.js";

const router = express.Router();

router.get("/", async (req, res) => {
  const db = getDbOrError(res);
  if (!db) return;

  const limit = parseLimit(req.query.limit, 100, 500);
  const type = parseString(req.query.type);
  const active = parseBoolean(req.query.active);
  const symbol = parseString(req.query.symbol);

  const conditions = [];
  const replacements = { limit };

  if (type) {
    conditions.push("type = :type");
    replacements.type = type;
  }

  if (active !== null) {
    conditions.push("is_active = :active");
    replacements.active = active;
  }

  if (symbol) {
    conditions.push("symbol = :symbol");
    replacements.symbol = symbol.toUpperCase();
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const query = `
    SELECT
      symbol,
      name,
      type,
      keywords,
      subreddits,
      is_active,
      created_at
    FROM assets
    ${whereClause}
    ORDER BY symbol ASC
    LIMIT :limit;
  `;

  try {
    const rows = await db.query(query, {
      type: QueryTypes.SELECT,
      replacements,
    });
    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to load assets", error);
    return res.status(500).json({ error: "Failed to load assets" });
  }
});

export default router;
