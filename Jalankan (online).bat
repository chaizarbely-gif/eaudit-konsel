@echo off
title e-Audit Konawe Selatan (ONLINE)
cd /d "%~dp0"
echo.
echo  ================================================
echo   e-Audit Kabupaten Konawe Selatan - MODE ONLINE
echo   Aplikasi dibuka ke internet lewat Cloudflare Tunnel (HTTPS)
echo   dengan alamat domain yang diatur di dasbor Cloudflare.
echo   Komputer ini harus tetap menyala dan terhubung internet.
echo   Tutup jendela ini untuk menghentikan akses online.
echo  ================================================
echo.
if not exist "tunnel\token.txt" (
  echo  [!] Berkas tunnel\token.txt belum ada.
  echo      Salin token tunnel dari dasbor Cloudflare ke berkas tersebut.
  pause
  exit /b 1
)
set /p TOKEN=<"tunnel\token.txt"
rem server aplikasi hanya mendengar di komputer ini (127.0.0.1); tunnel yang meneruskan ke internet
start "e-Audit Konawe Selatan (server)" /min cmd /c "python -u app.py || py -u app.py"
timeout /t 5 /nobreak >nul
"tunnel\cloudflared.exe" tunnel --no-autoupdate run --token %TOKEN%
pause
