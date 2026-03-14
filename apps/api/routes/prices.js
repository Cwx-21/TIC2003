import express from "express";
import { QueryTypes } from "sequelize";
import { parseLimit, parseString } from "../utils/query.js";
import { getDbOrError, normalizeSymbol } from "../utils/task2_2.js";

const router = express.Router();

router.get("/:symbol", async (req, res) => {
  const db = getDbOrError(res);
  if (!db) return;

  const symbol = normalizeSymbol(req.params.symbol);
  if (!symbol) {
    return res.status(400).json({ error: "Symbol is required" });
  }

  const limit = parseLimit(req.query.limit, 200, 1000);
  const source = parseString(req.query.source);
  const startDate = parseString(req.query.start_date);
  const endDate = parseString(req.query.end_date);

  const conditions = ["asset_symbol = :symbol"];
  const replacements = { symbol, limit };

  if (source) {
    conditions.push("source = :source");
    replacements.source = source;
  }

  if (startDate) {
    conditions.push("event_date >= :startDate");
    replacements.startDate = startDate;
  }

  if (endDate) {
    conditions.push("event_date <= :endDate");
    replacements.endDate = endDate;
  }

  const whereClause = `WHERE ${conditions.join(" AND ")}`;

  const query = `
    SELECT
      event_date,
      price_open,
      price_close,
      price_high,
      price_low,
      volume,
      source
    FROM historical_prices
    ${whereClause}
    ORDER BY event_date DESC
    LIMIT :limit;
  `;

  try {
    const rows = await db.query(query, {
      type: QueryTypes.SELECT,
      replacements,
    });
    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to load prices", error);
    return res.status(500).json({ error: "Failed to load prices" });
  }
});

export default router;
