@echo off
cd %~dp0
poetry run python ./automatic_volume_transfer.py

:: Keeps the terminal open if an error is encountered
if %errorlevel% neq 0 (
    echo Error encountered during script execution.
    pause
)