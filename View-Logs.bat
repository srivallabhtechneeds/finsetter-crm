@echo off
REM Tails the Odoo container's logs. Press Ctrl+C to stop watching
REM (this does not stop the containers themselves).
setlocal
cd /d "%~dp0"
title Finsetter CRM - Logs
docker compose logs -f odoo
endlocal
