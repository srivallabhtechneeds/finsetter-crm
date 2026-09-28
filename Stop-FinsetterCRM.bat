@echo off
REM Stops the Finsetter CRM containers. Data is kept (the database volume
REM is untouched). Pass -v as an argument to also wipe the database:
REM    Stop-FinsetterCRM.bat -v
setlocal
cd /d "%~dp0"
title Finsetter CRM - Stop

if "%~1"=="-v" (
    echo This will STOP the containers AND DELETE the database. Data will be lost.
    set /p CONFIRM=Type YES to continue:
    if /I not "%CONFIRM%"=="YES" (
        echo Cancelled.
        goto :end
    )
    docker compose down -v
) else (
    docker compose down
)

:end
pause
endlocal
