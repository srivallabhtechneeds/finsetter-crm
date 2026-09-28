#!/usr/bin/env bash
# Apply code/data changes to an already-installed finsetter_crm without
# recreating the database (odoo -u = update module).
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec odoo odoo -d "${ODOO_DB_NAME:-finsetter_crm}" -u finsetter_crm --stop-after-init --no-http
docker compose restart odoo
