@echo off
echo ============================================================
echo   WO Mic Recording ^& Streaming System
echo ============================================================
echo.
echo Kiem tra Python...
python --version
echo.
echo Cai dat dependencies...
pip install -r requirements.txt --quiet
echo.
echo Khoi dong he thong...
python main.py
pause
