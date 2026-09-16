@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py avatar_agent.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python avatar_agent.py
  goto :eof
)
echo Python was not found. Install Python 3.10+ and run this file again.
pause
