import express from "express";
import { QueryTypes } from "sequelize";
import sequelize, { hasDbConfig } from "../database/index.js";
import { parseLimit, parsePositiveInt, parseString } from "../utils/query.js";

const router = express.Router();

router.get("/", async (req, res) => {
  if (!hasDbConfig || !sequelize) {
    return res.status(500).json({ error: "DATABASE_URL is not configured" });
  }

  const limit = parseLimit(req.query.limit, 50, 200);
  const status = parseString(req.query.status);
  const id = parsePositiveInt(req.query.id);

  const conditions = [];
  const replacements = { limit };

  if (status) {
    conditions.push("ls.status = :status");
    replacements.status = status;
  }

  if (id) {
    conditions.push("ls.id = :id");
    replacements.id = id;
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const query = `
    SELECT
      ls.id,
      ls.name,
      ls.status,
      ls.channels_monitored,
      ls.assets_tracked,
      ls.started_at,
      ls.ended_at,
      ls.total_messages_processed,
      ls.parameters,
      COALESCE(c.correlation_points, 0) AS correlation_points,
      c.avg_divergence,
      c.avg_sentiment,
      c.avg_price_change_pct,
      COALESCE(a.alert_count, 0) AS alert_count,
      a.latest_alert_at
    FROM live_sessions ls
    LEFT JOIN (
      SELECT
        session_id,
        COUNT(*)::int AS correlation_points,
        AVG(sentiment_price_divergence) AS avg_divergence,
        AVG(avg_sentiment) AS avg_sentiment,
        AVG(price_change_pct) AS avg_price_change_pct
      FROM sentiment_price_correlation
      WHERE session_id IS NOT NULL
      GROUP BY session_id
    ) c ON c.session_id = ls.id
    LEFT JOIN (
      SELECT
        session_id,
        COUNT(*)::int AS alert_count,
        MAX(event_timestamp) AS latest_alert_at
      FROM alerts
      WHERE session_id IS NOT NULL
      GROUP BY session_id
    ) a ON a.session_id = ls.id
    ${whereClause}
    ORDER BY ls.started_at DESC
    LIMIT :limit;
  `;

  try {
    const rows = await sequelize.query(query, {
      type: QueryTypes.SELECT,
      replacements,
    });
    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to load sessions", error);
    return res.status(500).json({ error: "Failed to load sessions" });
  }
});

export default router;
