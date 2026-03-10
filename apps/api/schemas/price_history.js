import { DataTypes } from "sequelize";
import db from "../database/connection.js";
import Assets from "./assets.js";

const Price_History = db.define(
  "price_history",
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
    price: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    currency: {
      type: DataTypes.STRING(5),
      allowNull: false,
      defaultValue: "USD",
    },
    event_timestamp: {
      type: DataTypes.DATE,
      allowNull: false,
    },
    backtest_id: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    session_id: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
  },
  {
    timestamps: true,
    underscored: true,
    updatedAt: false,
    freezeTableName: true,
  },
);

Assets.hasMany(Price_History, {
  foreignKey: "asset_symbol",
  as: "Price_History",
});
Price_History.belongsTo(Assets, {
  foreignKey: "asset_symbol",
  as: "Assets",
});

export default Price_History;
