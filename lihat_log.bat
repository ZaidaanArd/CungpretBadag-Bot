@echo off
title Bot Log
cd /d "%~dp0"
if not exist bot.log (
    echo Belum ada log.
    pause
    exit /b
)
echo ===== 20 BARIS TERAKHIR =====
powershell -Command "Get-Content bot.log -Tail 20"
echo.
echo ==============================
echo File lengkap: bot.log
pause