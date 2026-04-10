/**
 * Sequelize Database Connection Pool
 *
 * Implements the Singleton pattern — a single Sequelize instance is created
 * on module load and shared across all importers. The instance is configured
 * with a connection pool whose size is tunable via environment variables:
 *   DB_POOL_MAX  — maximum open connections (default 10)
 *   DB_POOL_MIN  — minimum idle connections (default 0)
 *   DB_POOL_IDLE — idle timeout in milliseconds (default 10000)
 *
 * If DATABASE_URL is not set, the module falls back to a local development
 * URL and exports hasDbConfig = false so callers can handle the unconfigured
 * state gracefully (e.g., returning 500 without crashing).
 */

import dotenv from "dotenv";
import { Sequelize } from "sequelize";

dotenv.config();

const databaseUrl = process.env.DATABASE_URL;
const fallbackDatabaseUrl =
  process.env.DATABASE_FALLBACK_URL ??
  "postgres://user:password@127.0.0.1:5432/hypecheck";

/** True when DATABASE_URL is present in the environment. */
export const hasDbConfig = Boolean(databaseUrl);

/** Singleton Sequelize instance shared across the entire API process. */
const sequelize = new Sequelize(databaseUrl ?? fallbackDatabaseUrl, {
  dialect: "postgres",
  logging: false,
  pool: {
    max: Number.parseInt(process.env.DB_POOL_MAX ?? "10", 10),
    min: Number.parseInt(process.env.DB_POOL_MIN ?? "0", 10),
    idle: Number.parseInt(process.env.DB_POOL_IDLE ?? "10000", 10),
  },
});

export default sequelize;
