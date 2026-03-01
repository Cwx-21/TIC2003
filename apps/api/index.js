import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import db from "./database/connection.js";
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

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

const onFirstLoad = false;

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.json({ message: "HypeCheck API is running" });
});

app.listen(PORT, async (err) => {
  if (err) {
    console.log(`Cannot Listen on PORT: ${PORT}`);
  } else {
    console.log(`Server is Listening on: http://localhost:${PORT}/`);

    await db
      .sync({ force: onFirstLoad })
      .then(async () => {
        console.log("Connection to PostgreSQL is successful");
      })
      .catch((error) => {
        console.log(`Failed to connect to PostgreSQL: ${error}`);
      });

    if (onFirstLoad) {
      try {
        const { LoadData } = require("./database/loadData.js");
        await LoadData();
      } catch (err) {
        console.log(err);
      }
    }
  }
});
