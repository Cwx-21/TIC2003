import { DataTypes } from "sequelize";
import db from "../database/connection.js";
import Assets from "./assets.js";
import Backtest_Run from "./backtest_runs.js";
import Live_Sessions from "./live_sessions.js";
import Author from "./author_credibility.js";

const Sentiments_Logs = db.define(
  "sentiment_logs",
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
    source: {
      type: DataTypes.STRING(20),
      allowNull: true,
    },
    content: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    sentiment_score: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    credibility_score: {
      type: DataTypes.FLOAT,
      allowNull: false,
    },
    raw_metadata: {
      type: DataTypes.JSONB,
      allowNull: false,
    },
    event_timestamp: {
      type: DataTypes.DATE,
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
    author_id: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
  },
  {
    timestamps: true,
    underscored: true,
    updatedAt: false,
    freezeTableName: true,
  },
);

Assets.hasMany(Sentiments_Logs, {
  foreignKey: "asset_symbol",
  as: "Sentiments_Logs",
});
Sentiments_Logs.belongsTo(Assets, {
  foreignKey: "asset_symbol",
  as: "Assets",
});

Backtest_Run.hasMany(Sentiments_Logs, {
  foreignKey: "backtest_id",
  as: "Sentiments_Logs",
});
Sentiments_Logs.belongsTo(Backtest_Run, {
  foreignKey: "backtest_id",
  as: "Backtest_Run",
});

Live_Sessions.hasMany(Sentiments_Logs, {
  foreignKey: "session_id",
  as: "Sentiments_Logs",
});
Sentiments_Logs.belongsTo(Live_Sessions, {
  foreignKey: "session_id",
  as: "Live_Sessions",
});

export default Sentiments_Logs;
