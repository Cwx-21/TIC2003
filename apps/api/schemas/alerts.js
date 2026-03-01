import { DataTypes } from "sequelize";
import db from "../database/connection.js";
import Assets from "./assets.js";
import Backtest_Run from "./backtest_runs.js";
import Live_Sessions from "./live_sessions.js";

const Alerts = db.define(
  "alerts",
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
    alert_type: {
      type: DataTypes.STRING(30),
      allowNull: true,
      validate: {
        isIn: [
          ["divergence", "volume_spike", "sentiment_reversal", "spam_surge"],
        ],
      },
    },
    severity: {
      type: DataTypes.STRING(10),
      allowNull: true,
      defaultValue: "info",
      validate: {
        isIn: [["info", "warning", "critical"]],
      },
    },
    message: {
      type: DataTypes.TEXT,
      allowNull: true,
    },

    details: {
      type: DataTypes.JSONB,
      allowNull: true,
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
    is_acknowledged: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: false,
    },
  },
  {
    timestamps: true,
    freezeTableName: true,
  },
);

Assets.hasMany(Alerts, { foreignKey: "asset_symbol", as: "Alerts" });
Alerts.belongsTo(Assets, { foreignKey: "asset_symbol", as: "Assets" });

Backtest_Run.hasMany(Alerts, {
  foreignKey: "backtest_id",
  as: "Alerts",
});
Alerts.belongsTo(Backtest_Run, {
  foreignKey: "backtest_id",
  as: "Backtest_Run",
});

Live_Sessions.hasMany(Alerts, {
  foreignKey: "session_id",
  as: "Alerts",
});
Alerts.belongsTo(Live_Sessions, {
  foreignKey: "session_id",
  as: "Live_Sessions",
});

export default Alerts;
