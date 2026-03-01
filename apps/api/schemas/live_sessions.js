import { DataTypes } from "sequelize";
import db from "../database/connection.js";

const Live_Sessions = db.define(
  "live_sessions",
  {
    id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true,
    },
    name: {
      type: DataTypes.STRING(100),
      allowNull: false,
    },
    status: {
      type: DataTypes.STRING(10),
      allowNull: true,
      validate: {
        isIn: [["running", "completed", "stopped", "error"]],
      },
    },
    channels_monitored: {
      type: DataTypes.JSONB,
      allowNull: true,
    },
    assets_tracked: {
      type: DataTypes.JSONB,
      allowNull: true,
    },
    started_at: {
      type: DataTypes.DATE,
      allowNull: true,
      defaultValue: DataTypes.NOW,
    },
    ended_at: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    total_messages_processed: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
    },
    parameters: {
      type: DataTypes.JSONB,
      allowNull: true,
    },
  },
  {
    freezeTableName: true,
  },
);

export default Live_Sessions;
