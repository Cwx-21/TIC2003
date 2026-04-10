/**
 * Database Connection Re-export
 *
 * Provides a named alias for the Sequelize singleton so that schemas
 * and other modules can import it as `db` without depending directly
 * on the index module path. All callers share the same pool instance.
 */

import sequelize from "./index.js";

export default sequelize;
