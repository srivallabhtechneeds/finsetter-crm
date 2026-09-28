#!/usr/bin/env bash
# Build and start Finsetter CRM (Odoo + PostgreSQL) in the background.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --build
echo
echo "Starting up... first boot installs finsetter_crm, which can take a"
echo "couple of minutes. Tail progress with: ./scripts/logs.sh"
echo "Then open: http://localhost:8069  (login: admin / admin)"
