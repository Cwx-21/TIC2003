import { DataTypes } from "sequelize";
import db from "../database/connection.js";

const Assets = db.define(
  "assets",
  {
    symbol: {
      type: DataTypes.STRING(20),
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING(100),
      allowNull: false,
    },
    type: {
      type: DataTypes.STRING(10),
      allowNull: true,
      validate: {
        isIn: [["crypto", "stock"]],
      },
    },
    keywords: {
      type: DataTypes.JSONB,
      allowNull: false,
      defaultValue: [],
    },
    subreddits: {
      type: DataTypes.JSONB,
      allowNull: false,
      defaultValue: [],
    },
    is_active: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: true,
    },
  },
  {
    timestamps: true,
    freezeTableName: true,
  },
);

export default Assets;
