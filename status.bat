@echo off
title Cek Status Bot
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if "%errorlevel%"=="0" (
    echo [%date% %time%] ✅ Bot SEDANG berjalan
) else (
    echo [%date% %time%] ❌ Bot TIDAK berjalan
)
echo.
echo Tekan tombol apa saja untuk keluar...
pause >nul
