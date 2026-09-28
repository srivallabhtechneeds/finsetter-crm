@echo off
REM Re-applies changes to the finsetter_crm module (new/changed views,
REM fields, data) WITHOUT deleting the database. Use this after editing
REM anything under addons\finsetter_crm\.
setlocal
cd /d "%~dp0"
title Finsetter CRM - Upgrade Module

echo Upgrading finsetter_crm module (this restarts Odoo briefly)...
docker compose exec odoo odoo -d finsetter_crm -u finsetter_crm --stop-after-init --no-http
if errorlevel 1 (
    echo.
    echo [ERROR] Upgrade failed - see output above.
    goto :end
)
docker compose restart odoo
echo.
echo Done. Give Odoo a few seconds, then refresh your browser tab.

:end
pause
endlocal
