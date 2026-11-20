@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Video Indirici - Web
if not exist "venv" (
    python -m venv venv || (echo [HATA] Python bulunamadi & pause & exit /b)
)
call venv\Scripts\activate
python -c "import flask, yt_dlp" >nul 2>&1 || python -m pip install -q -U -r requirements.txt
where ffmpeg >nul 2>&1 || echo [UYARI] ffmpeg bulunamadi: winget install ffmpeg
where deno >nul 2>&1 || echo [UYARI] deno bulunamadi: winget install DenoLand.Deno
python web_app.py %*
pause
