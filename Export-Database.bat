@echo off
REM Saves the current Finsetter CRM data into the db\ folder so it can be
REM committed to Git. Anyone who clones the repo then gets this exact data.
REM Finsetter CRM must be running (Start-FinsetterCRM.bat) first.
setlocal
cd /d "%~dp0"
title Finsetter CRM - Export Database
if not exist db mkdir db
echo Dumping database to db\finsetter_crm.dump ...
docker compose exec -T db pg_dump -U odoo -Fc --no-owner --no-privileges finsetter_crm > db\finsetter_crm.dump
if errorlevel 1 goto :fail
echo Archiving uploaded files to db\filestore.tar.gz ...
docker compose exec -T odoo tar -czf - -C /var/lib/odoo/.local/share/Odoo/filestore/finsetter_crm . > db\filestore.tar.gz
if errorlevel 1 goto :fail
echo.
echo Snapshot updated. To share it, commit and push the db folder:
echo    git add db
echo    git commit -m "Update database snapshot"
echo    git push orgin main
goto :end
:fail
echo.
echo [ERROR] Export failed - is Finsetter CRM running? See output above.
:end
pause
endlocal
