import dotenv from "dotenv";
import { Sequelize } from "sequelize";

dotenv.config();

const databaseUrl = process.env.DATABASE_URL;

export const hasDbConfig = Boolean(databaseUrl);

const sequelize = hasDbConfig
  ? new Sequelize(databaseUrl, {
      dialect: "postgres",
      logging: false,
      pool: {
        max: Number.parseInt(process.env.DB_POOL_MAX ?? "10", 10),
        min: Number.parseInt(process.env.DB_POOL_MIN ?? "0", 10),
        idle: Number.parseInt(process.env.DB_POOL_IDLE ?? "10000", 10),
      },
    })
  : null;

export default sequelize;
