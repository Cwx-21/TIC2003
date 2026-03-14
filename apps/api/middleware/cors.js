// builds Express CORS middleware
import cors from "cors";
// load environment variables into process.env
import dotenv from "dotenv";

dotenv.config();

const defaultOrigins = ["http://localhost:5173", "http://127.0.0.1:5173"];
// CORS_ORIGINS from runtime environment 
const extraOrigins = (process.env.CORS_ORIGINS || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const allowedOrigins = new Set([...defaultOrigins, ...extraOrigins]);

const corsOptions = {
  origin(origin, callback) {
    if (!origin) {
      return callback(null, true);
    }
    // Compares that incoming Origin header against allowedOrigins
    if (allowedOrigins.has(origin)) {
      return callback(null, true);
    }
    return callback(null, false);
  },
  credentials: true,
};

export const corsMiddleware = cors(corsOptions);
export { allowedOrigins, corsOptions };
