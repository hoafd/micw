@echo off
title WO Mic System
echo ============================================================
echo   WO Mic Recording ^& Streaming System
echo ============================================================
echo.
echo 1. Chay kem Console (Hien thi log)
echo 2. Chay an ngam (Khong hien thi cua so)
echo.
set /p choice="Chon che do (1 hoac 2) [Mac dinh: 1]: "

echo.
echo Kiem tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Khong tim thay Python! Vui long cai dat Python.
    pause
    exit /b
)

echo Cai dat dependencies...
pip install -r requirements.txt --quiet
echo.

if "%choice%"=="2" (
    echo Khoi dong he thong - che do an...
    start "" pythonw main.py
    echo.
    echo He thong dang chay an! 
    echo Truy cap http://localhost:5000 de xem.
    echo Ban co the tat cua so nay, he thong van se hoat dong.
    echo ------------------------------------------------------------
    echo Dung file stop.bat de tat he thong khi khong su dung nua.
    timeout /t 10 >nul
) else (
    echo Khoi dong he thong - kem Console...
    python main.py
    pause
)
