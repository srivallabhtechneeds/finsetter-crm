@echo off
REM Replaces THIS machine's Finsetter CRM data with the snapshot in db\.
REM Everything currently in the local database is deleted.
REM Fresh clones do NOT need this - the snapshot loads automatically on
REM first start. Use it to reset an existing install to the shared data.
setlocal
cd /d "%~dp0"
title Finsetter CRM - Restore Database
if not exist db\finsetter_crm.dump (
    echo [ERROR] db\finsetter_crm.dump not found.
    goto :end
)
echo This DELETES the local finsetter_crm database and loads db\finsetter_crm.dump.
set /p answer=Type YES to continue:
if not "%answer%"=="YES" (
    echo Cancelled.
    goto :end
)
docker compose up -d db
docker compose stop odoo
docker compose exec -T db dropdb -U odoo --if-exists finsetter_crm
docker compose exec -T db createdb -U odoo finsetter_crm
docker compose exec -T -e POSTGRES_DB=finsetter_crm db bash /docker-entrypoint-initdb.d/10-restore-finsetter.sh
if errorlevel 1 (
    echo [ERROR] Restore failed - see output above.
    goto :end
)
docker compose run --rm --no-deps --entrypoint sh odoo -c "rm -rf /var/lib/odoo/.local/share/Odoo/filestore/finsetter_crm"
docker compose up -d odoo
echo.
echo Restored. Give Odoo a few seconds, then open http://localhost:8069
:end
pause
endlocal
