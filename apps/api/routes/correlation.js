import express from "express";
import { QueryTypes } from "sequelize";
import { parseLimit, parseString, parsePositiveInt } from "../utils/query.js";
import { getDbOrError, normalizeSymbol } from "../utils/task2_2.js";

const router = express.Router();

router.get("/:symbol", async (req, res) => {
  const db = getDbOrError(res);
  if (!db) return;

  const symbol = normalizeSymbol(req.params.symbol);
  if (!symbol) {
    return res.status(400).json({ error: "Symbol is required" });
  }

  const limit = parseLimit(req.query.limit, 200, 500);
  const interval = parseString(req.query.interval);
  const backtestId = parsePositiveInt(req.query.backtest_id);
  const sessionId = parsePositiveInt(req.query.session_id);

  const conditions = ["asset_symbol = :symbol"];
  const replacements = { symbol, limit };

  if (interval) {
    conditions.push("bucket_interval = :interval");
    replacements.interval = interval;
  }

  if (backtestId) {
    conditions.push("backtest_id = :backtestId");
    replacements.backtestId = backtestId;
  }

  if (sessionId) {
    conditions.push("session_id = :sessionId");
    replacements.sessionId = sessionId;
  }

  const whereClause = `WHERE ${conditions.join(" AND ")}`;

  const query = `
    SELECT
      time_bucket,
      bucket_interval,
      avg_sentiment,
      weighted_sentiment,
      price_at_bucket,
      price_change_pct,
      sentiment_price_divergence,
      message_volume,
      backtest_id,
      session_id,
      created_at
    FROM sentiment_price_correlation
    ${whereClause}
    ORDER BY time_bucket DESC
    LIMIT :limit;
  `;

  try {
    const rows = await db.query(query, {
      type: QueryTypes.SELECT,
      replacements,
    });
    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to load correlation", error);
    return res.status(500).json({ error: "Failed to load correlation" });
  }
});

export default router;
