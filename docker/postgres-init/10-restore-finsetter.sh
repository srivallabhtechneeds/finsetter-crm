#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Runs ONCE, when the PostgreSQL data volume is first created (fresh clone /
# fresh machine). Loads the Finsetter CRM database snapshot from db/ so a new
# checkout starts with exactly the same data as the repository owner.
# Existing installations are never touched: Postgres skips this folder when
# its data directory already exists.
# ---------------------------------------------------------------------------
set -euo pipefail

DUMP=/seed/finsetter_crm.dump
DB="${POSTGRES_DB:-finsetter_crm}"

if [ ! -f "$DUMP" ]; then
    echo "finsetter: no snapshot at $DUMP - starting with an empty database"
    exit 0
fi

echo "finsetter: restoring snapshot into database '$DB'..."
# Recreate the database the way Odoo creates its own (C collation), so list
# ordering matches the original install exactly.
dropdb -U "$POSTGRES_USER" --if-exists "$DB"
createdb -U "$POSTGRES_USER" -T template0 -E UTF8 --lc-collate=C --lc-ctype=en_US.utf8 "$DB"
pg_restore --no-owner --no-privileges --exit-on-error \
    -U "$POSTGRES_USER" -d "$DB" "$DUMP"

# Every copy gets its own secrets, so clones never share session-signing keys.
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$DB" <<'SQL'
UPDATE ir_config_parameter SET value = gen_random_uuid()::text
 WHERE key IN ('database.secret', 'database.uuid');
SQL

echo "finsetter: snapshot restored."
