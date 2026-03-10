import { DataTypes } from "sequelize";
import db from "../database/connection.js";

const Author_Credibility = db.define(
  "author_credibility",
  {
    author_id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true,
      allowNull: false,
    },
    source: {
      type: DataTypes.STRING(20),
      primaryKey: true,
      allowNull: false,
    },
    baseline_credibility: {
      type: DataTypes.FLOAT,
      allowNull: true,
      defaultValue: 1.0,
    },
    total_posts: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
    },
    spam_flags: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
    },
    is_bot: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
      defaultValue: false,
    },
    last_evaluated_at: {
      type: DataTypes.DATE,
      allowNull: true,
    },
  },
  {
    timestamps: false,
    freezeTableName: true,
  },
);

export default Author_Credibility;
