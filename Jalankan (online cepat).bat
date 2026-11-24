@echo off
title e-Audit Konawe Selatan (ONLINE SEMENTARA)
cd /d "%~dp0"
echo.
echo  ================================================
echo   e-Audit Kabupaten Konawe Selatan - ONLINE SEMENTARA
echo   Cari baris berisi alamat  https://....trycloudflare.com  di bawah,
echo   lalu buka alamat itu dari ponsel/komputer mana saja.
echo   Alamat BERUBAH setiap kali berkas ini dijalankan ulang.
echo   Tutup jendela ini untuk menghentikan akses online.
echo  ================================================
echo.
start "e-Audit Konawe Selatan (server)" /min cmd /c "python -u app.py || py -u app.py"
timeout /t 5 /nobreak >nul
"tunnel\cloudflared.exe" tunnel --no-autoupdate --url http://localhost:8080
pause
