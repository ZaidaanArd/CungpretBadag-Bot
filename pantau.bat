@echo off
title Pantau Bot - Real-time
cd /d "%~dp0"
if not exist activity.log (
    echo Belum ada aktivitas. Jalankan bot dulu.
    pause
    exit /b
)
echo Memantau aktivitas bot... (tekan Ctrl+C untuk keluar)
echo ========================================
powershell -Command "Get-Content activity.log -Tail 0 -Wait"
