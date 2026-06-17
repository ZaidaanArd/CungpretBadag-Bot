@echo off
title Stop Bot
echo Mencari proses bot...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if "%errorlevel%"=="0" (
    taskkill /F /IM python.exe >NUL
    echo [%date% %time%] ✅ Bot berhasil dihentikan
) else (
    echo [%date% %time%] ❌ Tidak ada bot yang berjalan
)
echo.
echo Tekan tombol apa saja untuk keluar...
pause >nul
