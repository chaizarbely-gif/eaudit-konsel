@echo off
title e-Audit Konawe Selatan
cd /d "%~dp0"
echo.
echo  ================================================
echo   e-Audit Kabupaten Konawe Selatan
echo   Alamat : http://localhost:8080
echo   Tutup jendela ini untuk menghentikan aplikasi.
echo  ================================================
echo.
start "" "http://localhost:8080/"
where python >nul 2>nul
if %errorlevel%==0 (
  python app.py
) else (
  py app.py
)
pause