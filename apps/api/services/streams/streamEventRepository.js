/**
 * Stream Event Repository — Repository Pattern
 *
 * Encapsulates all Sequelize persistence operations for the
 * stream_ingestion_events table. By centralising database access here,
 * the StreamIngestionFacade and route handlers remain decoupled from the
 * ORM layer and can be tested with a mock repository implementation.
 *
 * The Repository pattern separates the domain logic (facade) from the
 * data access layer, allowing the underlying storage mechanism to change
 * without affecting callers.
 */

import Stream_Ingestion_Events from "../../schemas/stream_ingestion_events.js";

/** Columns returned by default — payload columns are excluded unless explicitly requested. */
const DEFAULT_ATTRIBUTES = [
  "id",
  "source",
  "stream_name",
  "format",
  "content_type",
  "structure_kind",
  "parser_key",
  /** payload_hash is included by default — it is a short fixed-length string
   *  used for non-repudiation verification and does not bloat list responses. */
  "payload_hash",
  "metadata",
  "original_size_bytes",
  "record_count",
  "status",
  "received_at",
  "created_at",
];

/** Payload columns — large and excluded by default to keep list responses lean. */
const PAYLOAD_ATTRIBUTES = ["payload_json", "payload_text", "payload_base64"];

/**
 * Repository for creating and querying stream ingestion events.
 *
 * All Sequelize calls are isolated within this class so that the facade
 * and route handlers never interact with the ORM directly.
 */
export class StreamEventRepository {
  /**
   * Persists a new stream ingestion event record.
   *
   * @param {object} record - Validated and normalised event data.
   * @returns {Promise<import('sequelize').Model>} The created Sequelize model instance.
   */
  async create(record) {
    return Stream_Ingestion_Events.create(record);
  }

  /**
   * Returns recent stream ingestion events, ordered by received_at descending.
   *
   * Payload columns are included only when filters.includePayload is true,
   * keeping the default response payload lean for list views.
   *
   * @param {object} [filters={}]
   * @param {string} [filters.source] - Filter by source identifier.
   * @param {string} [filters.format] - Filter by canonical format string.
   * @param {string} [filters.structure_kind] - Filter by structure classification.
   * @param {boolean} [filters.includePayload=false] - Include payload columns in results.
   * @param {number} [filters.limit] - Maximum number of rows to return.
   *
   * @returns {Promise<import('sequelize').Model[]>} Array of Sequelize model instances.
   */
  async listRecent(filters = {}) {
    const where = {};

    if (filters.source) {
      where.source = filters.source;
    }
    if (filters.format) {
      where.format = filters.format;
    }
    if (filters.structure_kind) {
      where.structure_kind = filters.structure_kind;
    }

    const attributes = filters.includePayload
      ? [...DEFAULT_ATTRIBUTES, ...PAYLOAD_ATTRIBUTES]
      : DEFAULT_ATTRIBUTES;

    return Stream_Ingestion_Events.findAll({
      where,
      attributes,
      order: [["received_at", "DESC"]],
      limit: filters.limit,
    });
  }
}

/** Shared repository instance used by the default StreamIngestionFacade. */
export const streamEventRepository = new StreamEventRepository();
