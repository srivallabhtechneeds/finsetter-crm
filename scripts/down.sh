#!/usr/bin/env bash
# Stop containers. Add --volumes to also wipe the database.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down "$@"
