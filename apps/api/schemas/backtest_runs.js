import { DataTypes } from "sequelize";
import db from "../database/connection.js";

const Backtest_Runs = db.define(
  "backtest_runs",
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
    dataset_source: {
      type: DataTypes.STRING(50),
      allowNull: true,
    },
    status: {
      type: DataTypes.STRING(20),
      allowNull: true,
      validate: {
        isIn: [["running", "completed", "failed"]],
      },
      defaultValue: "running",
    },

    start_time: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    end_time: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    parameters: {
      type: DataTypes.JSONB,
      allowNull: true,
    },
    total_rows: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    processed_rows: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
    },
    error_count: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
    },
  },
  {
    timestamps: true,
    underscored: true,
    updatedAt: false,
    freezeTableName: true,
  },
);

export default Backtest_Runs;
