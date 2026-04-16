/**
 * Sentiment Route — GET /api/sentiment/:symbol
 *
 * Returns pre-computed sentiment aggregation records for a given asset.
 * Each record represents a time-bucketed summary (avg + credibility-weighted
 * average) computed by the SentimentAggregator or LiveProcessor.
 *
 * Route Parameters:
 *   symbol      {string} Asset ticker (e.g., 'BTC', 'TSLA'). Required.
 *
 * Query Parameters:
 *   limit        {number} Max rows to return (default 200, max 500).
 *   interval     {string} Bucket interval filter ('1h', '4h', '1d', '1m').
 *   backtest_id  {number} Filter by backtest run ID.
 *   session_id   {number} Filter by live session ID.
 */

import express from "express";
import { QueryTypes } from "sequelize";
import { parseLimit, parseString, parsePositiveInt } from "../utils/query.js";
import { getDbOrError, normalizeSymbol } from "../utils/task2_2.js";

const router = express.Router();

/**
 * GET /api/sentiment/:symbol
 * Returns sentiment aggregation records for the specified asset, ordered
 * by most recent time bucket first.
 */
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

  // asset_symbol is always required; bucket interval and run IDs are optional
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
      avg_sentiment_score,
      weighted_avg_sentiment,
      message_volume,
      backtest_id,
      session_id,
      created_at
    FROM sentiment_aggregations
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
    console.error("Failed to load sentiment", error);
    return res.status(500).json({ error: "Failed to load sentiment" });
  }
});

router.get("/:symbol/logs", async (req, res) => {
	const db = getDbOrError(res);
	if (!db) return;

	const symbol = normalizeSymbol(req.params.symbol);
	const backtestId = parsePositiveInt(req.query.backtest_id);

	if (!symbol) {
		return res.status(400).json({ error: "Symbol is required" });
	}

	try {
		const rows = await db.query(
			`
			SELECT
				id,
				content,
				sentiment_score,
				event_timestamp,
        raw_metadata->>'url' AS url
			FROM sentiment_logs
			WHERE asset_symbol = :symbol
			AND backtest_id = :backtestId
			ORDER BY event_timestamp DESC
			LIMIT 50
			`,
			{
				type: QueryTypes.SELECT,
				replacements: {
					symbol,
					backtestId,
				},
			}
		);

		return res.json({ data: rows });
	} catch (error) {
		console.error("Failed to load sentiment logs", error);
		return res.status(500).json({ error: "Failed to load sentiment logs" });
	}
});

export default router;
