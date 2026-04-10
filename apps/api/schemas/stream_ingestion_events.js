/**
 * Stream Ingestion Events — Sequelize Model
 *
 * Defines the ORM schema for the stream_ingestion_events table, which acts
 * as a generic landing zone for all inbound streaming payloads regardless
 * of format. Three mutually exclusive payload columns cover the three
 * structural categories:
 *
 *   payload_json   — Parsed structured payload (JSON/CSV/XML summary).
 *   payload_text   — Raw text string (XML, plain text).
 *   payload_base64 — Base64-encoded binary (XLS, XLSX, octet-stream).
 *
 * The structure_kind column classifies the payload into one of three tiers:
 *   'structured'      — fully parsed, machine-readable (JSON, CSV, spreadsheets).
 *   'semi_structured' — partially parsed with raw text preserved (XML).
 *   'unstructured'    — raw text or binary with no structural parsing (txt, binary).
 */

import { DataTypes } from "sequelize";
import db from "../database/connection.js";

/** Sequelize model for the stream_ingestion_events table. */
const Stream_Ingestion_Events = db.define(
  "stream_ingestion_events",
  {
    id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true,
    },
    /** Identifies the upstream data source (e.g., 'kafka-prod', 'webhook-api'). */
    source: {
      type: DataTypes.STRING(100),
      allowNull: false,
    },
    /** Logical stream name within the source (defaults to 'default'). */
    stream_name: {
      type: DataTypes.STRING(120),
      allowNull: false,
      defaultValue: "default",
    },
    /** Canonical format string resolved by the ingestion facade. */
    format: {
      type: DataTypes.STRING(20),
      allowNull: false,
    },
    /** Normalised MIME type string from the request Content-Type header. */
    content_type: {
      type: DataTypes.STRING(120),
      allowNull: false,
    },
    /** Structural classification of the payload. */
    structure_kind: {
      type: DataTypes.STRING(20),
      allowNull: false,
      validate: {
        isIn: [["structured", "semi_structured", "unstructured"]],
      },
    },
    /** Identifier of the concrete parser that processed the payload. */
    parser_key: {
      type: DataTypes.STRING(40),
      allowNull: false,
    },
    /** Parsed or structural representation of the payload (nullable for binary). */
    payload_json: {
      type: DataTypes.JSONB,
      allowNull: true,
    },
    /** Raw text content (populated for XML and plain text formats). */
    payload_text: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    /** Base64-encoded binary payload (populated for XLS, XLSX, and binary formats). */
    payload_base64: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    /**
     * SHA-256 hex digest of the raw payload at ingest time.
     * Stored for non-repudiation: proves exactly what bytes were received.
     * Nullable for legacy records created before Task 2.7.
     */
    payload_hash: {
      type: DataTypes.CHAR(64),
      allowNull: true,
    },
    /** Arbitrary key-value metadata attached by the caller at ingest time. */
    metadata: {
      type: DataTypes.JSONB,
      allowNull: false,
      defaultValue: {},
    },
    /** Byte size of the original raw payload before parsing. */
    original_size_bytes: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 0,
    },
    /** Number of logical records detected in the payload (e.g., CSV rows). */
    record_count: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 1,
    },
    /** Processing status — 'accepted' on successful ingest, 'rejected' on error. */
    status: {
      type: DataTypes.STRING(20),
      allowNull: false,
      defaultValue: "accepted",
      validate: {
        isIn: [["accepted", "rejected"]],
      },
    },
    /** UTC timestamp when the payload was received by the API. */
    received_at: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW,
    },
  },
  {
    timestamps: true,
    underscored: true,
    updatedAt: false,
    freezeTableName: true,
  },
);

export default Stream_Ingestion_Events;
