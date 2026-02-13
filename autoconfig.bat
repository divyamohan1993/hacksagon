@echo off
setlocal EnableDelayedExpansion
:: ============================================================================
::  ECO-LENS AUTOCONFIG — Idempotent Setup, Key Rotation ^& Launch  (Windows)
::  Re-run to rotate all security keys.   Usage:  autoconfig.bat
:: ============================================================================

set "BACKEND_PORT=40881"
set "FRONTEND_PORT=40882"
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"
set "LOGS_DIR=%PROJECT_DIR%\logs"
set "ENV_FILE=%PROJECT_DIR%\.env"
set "BACKEND_ENV=%BACKEND_DIR%\.env"
set "PID_BACKEND=%LOGS_DIR%\backend.pid"
set "PID_FRONTEND=%LOGS_DIR%\frontend.pid"

echo.
echo  ======================================================
echo   ECO-LENS AUTOCONFIG v1.0
echo   Virtual Air Quality Matrix
echo   Idempotent Setup / Key Rotation / Launch
echo  ======================================================
echo.

:: ============================================================================
:: STEP 1 — Check prerequisites
:: ============================================================================
echo [STEP] 1/7  Checking prerequisites...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 not found.
    echo         Install from https://www.python.org/downloads/
    echo         or run:  winget install Python.Python.3.11
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo [INFO]  Python %PY_VER%

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    echo         Install from https://nodejs.org/
    echo         or run:  winget install OpenJS.NodeJS.LTS
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set "NODE_VER=%%v"
echo [INFO]  Node %NODE_VER%

npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('npm --version') do set "NPM_VER=%%v"
echo [INFO]  npm %NPM_VER%

:: ============================================================================
:: STEP 2 — Stop existing processes
:: ============================================================================
echo [STEP] 2/7  Stopping existing Eco-Lens processes...

if exist "%PID_BACKEND%" (
    set /p B_PID=<"%PID_BACKEND%"
    taskkill /PID !B_PID! /F >nul 2>&1
    del /q "%PID_BACKEND%" >nul 2>&1
    echo [INFO]  Stopped backend PID !B_PID!
)
if exist "%PID_FRONTEND%" (
    set /p F_PID=<"%PID_FRONTEND%"
    taskkill /PID !F_PID! /F >nul 2>&1
    del /q "%PID_FRONTEND%" >nul 2>&1
    echo [INFO]  Stopped frontend PID !F_PID!
)

:: Kill by port as fallback
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo [INFO]  Freed port %BACKEND_PORT% ^(PID %%p^)
)
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo [INFO]  Freed port %FRONTEND_PORT% ^(PID %%p^)
)

timeout /t 2 /nobreak >nul 2>&1

:: ============================================================================
:: STEP 3 — Generate / Rotate Security Keys & Write .env
:: ============================================================================
echo [STEP] 3/7  Generating / rotating cryptographic keys...

:: Preserve user values
set "PREV_OWM=your_openweathermap_api_key_here"
set "PREV_CAM1="
set "PREV_CAM2="
set "PREV_CAM3="
set "PREV_SIM=true"

if exist "%ENV_FILE%" (
    echo [WARN]  Existing .env found — rotating ALL security keys

    :: Backup with timestamp
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value 2^>nul ^| find "="') do set "DT=%%a"
    set "BACKUP=%ENV_FILE%.backup.!DT:~0,8!_!DT:~8,6!"
    copy /y "%ENV_FILE%" "!BACKUP!" >nul 2>&1
    echo [INFO]  Backup saved to !BACKUP!

    :: Parse preserved values
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        if "%%a"=="OPENWEATHERMAP_API_KEY" set "PREV_OWM=%%b"
        if "%%a"=="CAMERA_FEED_URL_1" set "PREV_CAM1=%%b"
        if "%%a"=="CAMERA_FEED_URL_2" set "PREV_CAM2=%%b"
        if "%%a"=="CAMERA_FEED_URL_3" set "PREV_CAM3=%%b"
        if "%%a"=="SIMULATION_MODE" set "PREV_SIM=%%b"
    )
)

:: Generate keys via Python secrets module (cross-platform)
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(32))"') do set "API_SECRET_KEY=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(32))"') do set "ENCRYPTION_KEY=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(64))"') do set "JWT_SECRET_KEY=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(32))"') do set "SESSION_SECRET=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(32))"') do set "DB_ENCRYPTION_KEY=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(48))"') do set "INTERNAL_AUTH_TOKEN=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(16))"') do set "CORS_SIGNING_KEY=%%k"
for /f "tokens=*" %%k in ('python -c "import secrets; print(secrets.token_hex(32))"') do set "WS_AUTH_TOKEN=%%k"

:: Write .env
> "%ENV_FILE%" (
    echo # ============================================
    echo # ECO-LENS — Auto-Generated Configuration
    echo # Re-run autoconfig.bat to rotate security keys
    echo # ============================================
    echo.
    echo # ---- Enterprise Security Keys ^(Auto-Rotated^) ----
    echo API_SECRET_KEY=!API_SECRET_KEY!
    echo ENCRYPTION_KEY=!ENCRYPTION_KEY!
    echo JWT_SECRET_KEY=!JWT_SECRET_KEY!
    echo SESSION_SECRET=!SESSION_SECRET!
    echo DB_ENCRYPTION_KEY=!DB_ENCRYPTION_KEY!
    echo INTERNAL_AUTH_TOKEN=!INTERNAL_AUTH_TOKEN!
    echo CORS_SIGNING_KEY=!CORS_SIGNING_KEY!
    echo WS_AUTH_TOKEN=!WS_AUTH_TOKEN!
    echo.
    echo # ---- Server ----
    echo HOST=0.0.0.0
    echo PORT=%BACKEND_PORT%
    echo FRONTEND_URL=http://localhost:%FRONTEND_PORT%
    echo.
    echo # ---- OpenWeatherMap API ----
    echo OPENWEATHERMAP_API_KEY=!PREV_OWM!
    echo.
    echo # ---- Mode ----
    echo SIMULATION_MODE=!PREV_SIM!
    echo.
    echo # ---- Camera Feed URLs ----
    echo CAMERA_FEED_URL_1=!PREV_CAM1!
    echo CAMERA_FEED_URL_2=!PREV_CAM2!
    echo CAMERA_FEED_URL_3=!PREV_CAM3!
    echo.
    echo # ---- Database ----
    echo DATABASE_URL=sqlite:///./ecolens.db
    echo.
    echo # ---- Processing ----
    echo FRAME_INTERVAL=5
    echo SENSOR_UPDATE_INTERVAL=5
    echo WEATHER_UPDATE_INTERVAL=300
    echo.
    echo # ---- Map ----
    echo MAP_CENTER_LAT=40.7580
    echo MAP_CENTER_LNG=-73.9855
    echo.
    echo # ---- Frontend ----
    echo NEXT_PUBLIC_API_URL=http://localhost:%BACKEND_PORT%
    echo NEXT_PUBLIC_WS_URL=ws://localhost:%BACKEND_PORT%/ws
)

:: Copy to backend
copy /y "%ENV_FILE%" "%BACKEND_ENV%" >nul 2>&1

echo [INFO]  8 security keys generated ^& rotated
echo [INFO]  API_SECRET  = !API_SECRET_KEY:~0,12!...
echo [INFO]  ENCRYPTION  = !ENCRYPTION_KEY:~0,12!...
echo [INFO]  JWT_SECRET  = !JWT_SECRET_KEY:~0,12!...

:: ============================================================================
:: STEP 4 — Backend setup
:: ============================================================================
echo [STEP] 4/7  Setting up Python backend...

cd /d "%BACKEND_DIR%"

if not exist "venv" (
    python -m venv venv
    echo [INFO]  Virtual environment created
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel -q 2>nul
pip install -r requirements.txt -q 2>nul
call deactivate

echo [INFO]  Backend dependencies installed/updated

:: ============================================================================
:: STEP 5 — Frontend setup
:: ============================================================================
echo [STEP] 5/7  Setting up Next.js frontend...

cd /d "%FRONTEND_DIR%"
call npm install --silent 2>nul

echo [INFO]  Frontend dependencies installed/updated

:: ============================================================================
:: STEP 6 — Firewall rules (Windows Firewall, idempotent)
:: ============================================================================
echo [STEP] 6/7  Configuring firewall rules...

netsh advfirewall firewall delete rule name="EcoLens-Backend" >nul 2>&1
netsh advfirewall firewall add rule name="EcoLens-Backend" dir=in action=allow protocol=tcp localport=%BACKEND_PORT% >nul 2>&1

netsh advfirewall firewall delete rule name="EcoLens-Frontend" >nul 2>&1
netsh advfirewall firewall add rule name="EcoLens-Frontend" dir=in action=allow protocol=tcp localport=%FRONTEND_PORT% >nul 2>&1

echo [INFO]  Firewall rules set for ports %BACKEND_PORT%, %FRONTEND_PORT%

:: ============================================================================
:: STEP 7 — Launch services
:: ============================================================================
echo [STEP] 7/7  Launching Eco-Lens services...

if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

:: ---- Start Backend ----
cd /d "%BACKEND_DIR%"
start "EcoLens-Backend" /min cmd /c "call venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --log-level info > "%LOGS_DIR%\backend.log" 2>&1"

:: Wait for backend PID
timeout /t 4 /nobreak >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    echo %%p> "%PID_BACKEND%"
    echo [INFO]  Backend started  PID=%%p  port=%BACKEND_PORT%
    goto :backend_started
)
echo [WARN]  Backend PID not yet detected — may still be starting
:backend_started

:: ---- Start Frontend ----
cd /d "%FRONTEND_DIR%"

set "NEXT_PUBLIC_API_URL=http://localhost:%BACKEND_PORT%"
set "NEXT_PUBLIC_WS_URL=ws://localhost:%BACKEND_PORT%/ws"

start "EcoLens-Frontend" /min cmd /c "set PORT=%FRONTEND_PORT% && npx next dev -p %FRONTEND_PORT% > "%LOGS_DIR%\frontend.log" 2>&1"

timeout /t 4 /nobreak >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    echo %%p> "%PID_FRONTEND%"
    echo [INFO]  Frontend started PID=%%p  port=%FRONTEND_PORT%
    goto :frontend_started
)
echo [WARN]  Frontend PID not yet detected — may still be starting
:frontend_started

:: ---- Health Check ----
echo [INFO]  Waiting for backend health-check...
set "ATTEMPTS=0"
:healthloop
if !ATTEMPTS! GEQ 30 goto :healthdone
set /a ATTEMPTS+=1
curl -sf "http://localhost:%BACKEND_PORT%/api/health" >nul 2>&1
if not errorlevel 1 (
    echo [INFO]  Backend health-check: PASSED
    goto :healthdone
)
timeout /t 1 /nobreak >nul 2>&1
goto :healthloop
:healthdone

cd /d "%PROJECT_DIR%"

echo.
echo  ======================================================
echo        ECO-LENS IS RUNNING
echo  ======================================================
echo.
echo   Dashboard :  http://localhost:%FRONTEND_PORT%
echo   API       :  http://localhost:%BACKEND_PORT%
echo   API Docs  :  http://localhost:%BACKEND_PORT%/docs
echo   WebSocket :  ws://localhost:%BACKEND_PORT%/ws
echo.
echo   Logs      :  %LOGS_DIR%\
echo   Config    :  %ENV_FILE%
echo.
echo   Re-run this script to rotate all security keys.
echo  ======================================================
echo.

endlocal
