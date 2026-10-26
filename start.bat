@echo off
title Nano Banana Pro Studio
cd /d "%~dp0"
echo ====================================================
echo   NANO BANANA PRO STUDIO - FREE AI IMAGE GENERATOR
echo   100% Free - Khong can dang nhap tai khoan Google
echo ====================================================
echo.
python server.py
if %errorlevel% neq 0 (
    echo.
    echo Khong tim thay Python, mo truc tiep index.html bang trinh duyet...
    start index.html
)
pause
