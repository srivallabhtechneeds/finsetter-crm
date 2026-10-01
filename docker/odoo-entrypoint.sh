#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Finsetter CRM - Odoo container entrypoint.
# On first start (fresh clone), unpacks the filestore snapshot from db/ so
# uploaded files (company logo, documents, images) match the database
# restored by docker/postgres-init. Then hands over to the stock Odoo
# entrypoint unchanged.
# ---------------------------------------------------------------------------
set -euo pipefail

DB_NAME="${FINSETTER_DB_NAME:-finsetter_crm}"
FILESTORE="/var/lib/odoo/.local/share/Odoo/filestore/${DB_NAME}"
SNAPSHOT=/seed/filestore.tar.gz

if [ ! -d "$FILESTORE" ] && [ -f "$SNAPSHOT" ]; then
    echo "finsetter: restoring filestore snapshot into ${FILESTORE}..."
    mkdir -p "$FILESTORE"
    tar -xzf "$SNAPSHOT" -C "$FILESTORE"
fi

exec /entrypoint.sh "$@"
