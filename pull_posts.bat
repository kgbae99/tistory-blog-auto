@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/3] git status...
git status

echo.
echo [2/3] git pull...
git pull
if errorlevel 1 (
    echo.
    echo [Error] git pull failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Done.
pause
exit /b 0