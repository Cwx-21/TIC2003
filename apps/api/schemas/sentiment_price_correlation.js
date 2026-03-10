import { DataTypes } from "sequelize";
import db from "../database/connection.js";
import Assets from "./assets.js";
import Backtest_Run from "./backtest_runs.js";
import Live_Sessions from "./live_sessions.js";

const Sentiment_Price_Correlation = db.define(
  "sentiment_price_correlation",
  {
    id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true,
    },
    asset_symbol: {
      type: DataTypes.STRING(20),
      allowNull: false,
      references: {
        model: Assets,
        key: "symbol",
      },
    },
    time_bucket: {
      type: DataTypes.DATE,
      allowNull: false,
    },
    bucket_interval: {
      type: DataTypes.STRING(10),
      allowNull: false,
      defaultValue: "1h",
    },
    avg_sentiment: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    weighted_sentiment: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    price_at_bucket: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    price_change_pct: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    sentiment_price_divergence: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    message_volume: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
    backtest_id: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: Backtest_Run,
        key: "id",
      },
    },
    session_id: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: Live_Sessions,
        key: "id",
      },
    },
  },
  {
    timestamps: true,
    underscored: true,
    updatedAt: false,
    freezeTableName: true,
  },
);

Assets.hasMany(Sentiment_Price_Correlation, {
  foreignKey: "asset_symbol",
  as: "Sentiment_Price_Correlation",
});
Sentiment_Price_Correlation.belongsTo(Assets, {
  foreignKey: "asset_symbol",
  as: "Assets",
});

Backtest_Run.hasMany(Sentiment_Price_Correlation, {
  foreignKey: "backtest_id",
  as: "Sentiment_Price_Correlation",
});
Sentiment_Price_Correlation.belongsTo(Backtest_Run, {
  foreignKey: "backtest_id",
  as: "Backtest_Run",
});

Live_Sessions.hasMany(Sentiment_Price_Correlation, {
  foreignKey: "session_id",
  as: "Sentiment_Price_Correlation",
});
Sentiment_Price_Correlation.belongsTo(Live_Sessions, {
  foreignKey: "session_id",
  as: "Live_Sessions",
});

export default Sentiment_Price_Correlation;
