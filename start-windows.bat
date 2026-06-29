@echo off
REM ===========================================================================
REM  eClerx SEO/AEO/GEO Assessment - one-click launcher for Windows.
REM  Double-click this file. First run takes a few minutes (it installs things);
REM  later runs are fast. Two black windows will open (the engine + the website)
REM  and your browser will open the app. Keep both windows open while using it.
REM ===========================================================================
setlocal
cd /d "%~dp0"

echo(
echo  eClerx SEO/AEO/GEO Assessment - starting up...
echo(

REM --- Check prerequisites -------------------------------------------------
where python >nul 2>nul || (
  echo [X] Python is not installed.
  echo     Install it from https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^),
  echo     then double-click this file again.
  echo(
  pause & exit /b 1
)
where npm >nul 2>nul || (
  echo [X] Node.js is not installed.
  echo     Install the "LTS" version from https://nodejs.org , then run this file again.
  echo(
  pause & exit /b 1
)

if not defined SECRET_KEY set SECRET_KEY=dev-local

REM --- Backend setup -------------------------------------------------------
echo  [1/3] Setting up the analysis engine ^(first run downloads packages^)...
cd backend
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || ( echo [X] Install failed. & pause & exit /b 1 )
alembic upgrade head
python -m app.seed
echo  [2/3] Launching the engine window...
start "eClerx Engine (keep open)" cmd /k "call .venv\Scripts\activate.bat ^&^& set SECRET_KEY=dev-local ^&^& uvicorn app.main:app --port 8000"
cd ..

REM --- Frontend setup ------------------------------------------------------
echo  [3/3] Setting up and launching the website window...
cd frontend
if not exist node_modules ( call npm install )
start "eClerx Website (keep open)" cmd /k "npm run dev"
cd ..

REM --- Open the browser ----------------------------------------------------
echo(
echo  Almost there - opening your browser at http://localhost:5173
echo  (if it says "can't connect", wait ~20 seconds and refresh.)
timeout /t 12 /nobreak >nul
start "" http://localhost:5173
echo(
echo  Done! Keep the two black windows open while you use the app.
echo  To stop everything later, just close those two windows.
echo(
pause
