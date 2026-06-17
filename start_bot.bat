@echo off
title Bot Discord
cd /d "%~dp0"
echo [%date% %time%] Bot dimulai... >> bot.log
python bot.py >> bot.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] Bot berhenti (kode: %errorlevel%) >> bot.log
)
echo [%date% %time%] Bot mati >> bot.log