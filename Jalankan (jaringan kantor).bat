@echo off
title e-Audit Konawe Selatan (jaringan kantor)
cd /d "%~dp0"
echo.
echo  ================================================
echo   e-Audit Kabupaten Konawe Selatan - MODE JARINGAN KANTOR
echo   Komputer lain di jaringan yang sama dapat membuka aplikasi
echo   lewat alamat yang tampil di bawah (http://IP-komputer-ini:8080).
echo   Tutup jendela ini untuk menghentikan aplikasi.
echo  ================================================
echo.
set EAUDIT_HOST=0.0.0.0
start "" "http://localhost:8080/"
where python >/dev/null 2>nul
if %errorlevel%==0 (
  python -u app.py
) else (
  py -u app.py
)
pause
