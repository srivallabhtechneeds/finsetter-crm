#!/usr/bin/env bash
# Save the CURRENT Finsetter CRM data into db/ so it can be committed and
# shared: anyone who clones the repo then starts with this exact data.
# Requires the stack to be running (Start-FinsetterCRM.bat / scripts/up.sh).
set -euo pipefail
# Git Bash on Windows would rewrite /var/... container paths; keep them as-is.
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
DB="${ODOO_DB_NAME:-finsetter_crm}"
FILESTORE="/var/lib/odoo/.local/share/Odoo/filestore/${DB}"

mkdir -p db
echo "Dumping database '${DB}' -> db/finsetter_crm.dump"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-odoo}" -Fc --no-owner --no-privileges "$DB" > db/finsetter_crm.dump.tmp
mv db/finsetter_crm.dump.tmp db/finsetter_crm.dump

echo "Archiving filestore -> db/filestore.tar.gz"
docker compose exec -T odoo tar -czf - -C "$FILESTORE" . > db/filestore.tar.gz.tmp
mv db/filestore.tar.gz.tmp db/filestore.tar.gz

ls -lh db/finsetter_crm.dump db/filestore.tar.gz
echo
echo "Snapshot updated. Commit db/ to share it:"
echo "  git add db && git commit -m \"Update database snapshot\" && git push"
