/**
 * Prices Route — GET /api/prices/:symbol
 *
 * Returns historical OHLCV price records for a given asset, sourced from
 * the historical_prices table (populated via yfinance during backtest runs).
 *
 * Route Parameters:
 *   symbol     {string} Asset ticker (e.g., 'BTC', 'TSLA'). Required.
 *
 * Query Parameters:
 *   limit      {number} Max rows to return (default 200, max 1000).
 *   source     {string} Filter by data source (e.g., 'yfinance').
 *   start_date {string} Inclusive lower bound for event_date ('YYYY-MM-DD').
 *   end_date   {string} Inclusive upper bound for event_date ('YYYY-MM-DD').
 */

import express from "express";
import { QueryTypes } from "sequelize";
import { parseLimit, parseString } from "../utils/query.js";
import { getDbOrError, normalizeSymbol } from "../utils/task2_2.js";

const router = express.Router();

/**
 * GET /api/prices/:symbol
 * Returns historical price records for the specified asset, ordered by
 * most recent date first.
 */
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

  // asset_symbol is always required; date range and source are optional
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
