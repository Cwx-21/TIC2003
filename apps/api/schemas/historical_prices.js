import { DataTypes } from "sequelize";
import db from "../database/connection.js";
import Assets from "./assets.js";

const Historical_Prices = db.define(
  "historical_prices",
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
    price_open: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    price_close: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    price_high: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    price_low: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    volume: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    source: {
      type: DataTypes.STRING(30),
      allowNull: true,
    },
    event_date: {
      type: DataTypes.DATEONLY,
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
    freezeTableName: true,
    indexes: [
      {
        unique: true,
        fields: ["asset_symbol", "event_date"],
      },
    ],
  },
);

Assets.hasMany(Historical_Prices, {
  foreignKey: "asset_symbol",
  as: "Historical_Prices",
});
Historical_Prices.belongsTo(Assets, {
  foreignKey: "asset_symbol",
  as: "Assets",
});

export default Historical_Prices;
