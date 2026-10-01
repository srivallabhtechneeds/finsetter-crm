#!/usr/bin/env bash
# Replace THIS machine's Finsetter CRM data with the snapshot in db/.
# Destructive: everything in the local finsetter_crm database is lost.
# Fresh clones do not need this - the snapshot is loaded automatically on
# first start. Use it to reset an existing install to the shared snapshot.
set -euo pipefail
# Git Bash on Windows would rewrite /var/... container paths; keep them as-is.
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
DB="${ODOO_DB_NAME:-finsetter_crm}"
PGUSER_="${POSTGRES_USER:-odoo}"

[ -f db/finsetter_crm.dump ] || { echo "db/finsetter_crm.dump not found"; exit 1; }
if [ "${1:-}" != "--yes" ]; then
    read -r -p "This DELETES the local '${DB}' database and loads db/finsetter_crm.dump. Type YES to continue: " answer
    [ "$answer" = "YES" ] || { echo "Cancelled."; exit 1; }
fi

docker compose up -d db
docker compose stop odoo
docker compose exec -T db dropdb -U "$PGUSER_" --if-exists "$DB"
docker compose exec -T db createdb -U "$PGUSER_" "$DB"
docker compose exec -T -e POSTGRES_DB="$DB" db bash /docker-entrypoint-initdb.d/10-restore-finsetter.sh
# Remove the old filestore; the Odoo entrypoint unpacks the snapshot on start.
docker compose run --rm --no-deps --entrypoint sh odoo -c "rm -rf /var/lib/odoo/.local/share/Odoo/filestore/${DB}"
docker compose up -d odoo
echo "Restored. Give Odoo a few seconds, then open http://localhost:8069"
