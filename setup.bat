@echo off
echo ECO-LENS Setup
echo ==================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.11+
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js not found. Please install Node.js 18+
    exit /b 1
)

REM Setup backend
echo Setting up backend...
cd backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

REM Setup frontend
echo Setting up frontend...
cd frontend
call npm install
cd ..

REM Check for .env
if not exist .env (
    echo No .env file found. Copying .env.example...
    copy .env.example .env
    echo Please edit .env with your API keys
)

echo.
echo Setup complete!
echo.
echo To start:
echo   Terminal 1: cd backend ^&^& venv\Scripts\activate ^&^& python -m uvicorn main:app --reload --port 8000
echo   Terminal 2: cd frontend ^&^& npm run dev
echo.
echo Dashboard: http://localhost:3000
echo API Docs:  http://localhost:8000/docs
