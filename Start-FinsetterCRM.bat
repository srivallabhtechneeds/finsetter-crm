@echo off
REM ============================================================
REM  Finsetter CRM — one-click start (Windows / Docker Desktop)
REM  Double-click this file, or run it from a CMD/PowerShell window.
REM  It must stay in the finsetter-crm folder, next to
REM  docker-compose.yml, for the paths below to work.
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Finsetter CRM

echo ============================================================
echo   Finsetter CRM launcher
echo ============================================================
echo.

REM ---- 1. Docker CLI present? ----
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] "docker" was not found on this machine.
    echo         Install Docker Desktop: https://www.docker.com/products/docker-desktop/
    echo         Then re-run this file.
    goto :end
)

REM ---- 2. Docker daemon actually running? ----
echo Checking Docker Desktop is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker CLI found, but the Docker daemon is not responding.
    echo         Open Docker Desktop from the Start menu, wait for the whale
    echo         icon in the system tray to stop animating, then re-run this file.
    goto :end
)
echo   OK - Docker is running.
echo.

REM ---- 3. docker-compose.yml present in this folder? ----
if not exist "%~dp0docker-compose.yml" (
    echo [ERROR] docker-compose.yml was not found next to this .bat file.
    echo         Make sure Start-FinsetterCRM.bat sits in the same folder
    echo         you unzipped finsetter-crm.zip into.
    goto :end
)

REM ---- 4. Build and start ----
echo Building and starting Finsetter CRM (first run can take a few minutes)...
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [ERROR] "docker compose up" failed - see the output above.
    goto :end
)

echo.
echo Containers started. Waiting for Odoo to finish loading modules...
echo (You can also watch this live in a separate window with:
echo    docker compose logs -f odoo)
echo.

REM ---- 5. Poll until Odoo answers on :8069, up to ~3 minutes ----
set /a tries=0
:waitloop
set /a tries+=1
curl -s -o nul -w "%%{http_code}" http://localhost:8069/web/login > "%TEMP%\finsetter_status.txt" 2>nul
set /p HTTP_CODE=<"%TEMP%\finsetter_status.txt"
if "%HTTP_CODE%"=="200" goto :ready
if %tries% GEQ 36 goto :timeout
timeout /t 2 /nobreak >nul
goto :waitloop

:ready
echo   OK - Odoo is responding.
echo.
echo Opening Finsetter CRM in your browser...
start "" "http://localhost:8069"
echo.
echo Login:  admin / admin   (change this immediately once logged in)
goto :end

:timeout
echo.
echo Odoo hasn't responded on http://localhost:8069 yet after ~3 minutes.
echo This can happen on a slow first build/install. Check progress with:
echo    docker compose logs -f odoo
echo Then open http://localhost:8069 yourself once you see "Modules loaded."
echo.

:end
echo ============================================================
pause
endlocal
