/**
 * HypeCheck API — Express Application Entry Point
 *
 * Initialises the Express server, registers global middleware (CORS, JSON
 * body parsing, rate limiting), mounts all route handlers, and establishes
 * the Sequelize database connection on startup.
 *
 * Route Layout:
 *   GET  /                                    Health check
 *   GET  /sentiment_aggregations/:symbol/latest  Latest sentiment buckets
 *   GET  /historical_price/:symbol/latest        Latest historical prices
 *   GET  /historical_price/:symbol               Price range query
 *   /api/alerts        → routes/alerts.js
 *   /api/assets        → routes/assets.js
 *   /api/backtests     → routes/backtests.js
 *   /api/correlation   → routes/correlation.js
 *   /api/prices        → routes/prices.js
 *   /api/sentiment     → routes/sentiment.js
 *   /api/sessions      → routes/sessions.js
 *   /api/streams       → routes/streams.js
 */

import express from "express";
import dotenv from "dotenv";
import { Op } from "sequelize";
import Alerts from "./schemas/alerts.js";
import Assets from "./schemas/assets.js";
import Author_Credibility from "./schemas/author_credibility.js";
import Backtest_Runs from "./schemas/backtest_runs.js";
import Historical_Prices from "./schemas/historical_prices.js";
import Live_Sessions from "./schemas/live_sessions.js";
import Price_History from "./schemas/price_history.js";
import Sentiment_Aggregations from "./schemas/sentiment_aggregations.js";
import Sentiment_Logs from "./schemas/sentiment_logs.js";
import Sentiment_Price_Correlation from "./schemas/sentiment_price_correlation.js";
import { corsMiddleware } from "./middleware/cors.js";
import rateLimit from "./middleware/rateLimit.js";
import alertsRouter from "./routes/alerts.js";
import backtestsRouter from "./routes/backtests.js";
import sessionsRouter from "./routes/sessions.js";
import assetsRouter from "./routes/assets.js";
import sentimentRouter from "./routes/sentiment.js";
import pricesRouter from "./routes/prices.js";
import correlationRouter from "./routes/correlation.js";
import streamsRouter from "./routes/streams.js";
import db, { hasDbConfig } from "./database/index.js";
import "./schemas/stream_ingestion_events.js";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Trust the first proxy hop so req.ip reflects the client IP correctly
app.set("trust proxy", 1);
app.use(corsMiddleware);
app.use(express.json({ limit: process.env.API_JSON_LIMIT ?? "1mb" }));
app.use("/api", rateLimit);

/** GET / — Confirms the API process is running. */
app.get("/", (req, res) => {
  res.json({ message: "HypeCheck API is running" });
});

app.use("/api/backtests", backtestsRouter);
app.use("/api/sessions", sessionsRouter);
app.use("/api/alerts", alertsRouter);
app.use("/api/assets", assetsRouter);
app.use("/api/sentiment", sentimentRouter);
app.use("/api/prices", pricesRouter);
app.use("/api/correlation", correlationRouter);
app.use("/api/streams", streamsRouter);

app.listen(PORT, async (err) => {
  if (err) {
    console.log(`Cannot Listen on PORT: ${PORT}`);
    return;
  }

  console.log(`Server is Listening on: http://localhost:${PORT}/`);

  if (hasDbConfig && db) {
    await db
      .sync()
      .then(async () => {
        console.log("Connection to PostgreSQL is successful");
      })
      .catch((error) => {
        console.log(`Failed to connect to PostgreSQL: ${error}`);
      });

    db.authenticate()
      .then(() => {
        console.log("Database connection established.");
      })
      .catch((error) => {
        console.error("Unable to connect to the database:", error);
      });
  } else {
    console.warn("DATABASE_URL is not set. API endpoints will return errors.");
  }
});
