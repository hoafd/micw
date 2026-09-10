@echo off
title Stop WO Mic System
echo ============================================================
echo   Dung he thong WO Mic Recording ^& Streaming
echo ============================================================
echo.
echo Dang tim va tat he thong (main.py)...

:: Su dung PowerShell de tim dung tien trinh python/pythonw dang chay file main.py trong thu muc hien tai
powershell -Command "$path = (Get-Item 'main.py').FullName.Replace('\', '\\'); Get-WmiObject Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match $path } | ForEach-Object { $_.Terminate() }"

echo.
echo He thong da duoc tat thanh cong!
echo.
pause
