@echo off
setlocal EnableExtensions

:: Her zaman bu betigin klasorunden calissin (cift tiklayinca garanti)
cd /d "%~dp0"

title YouTube Video Indiricisi
echo ================================
echo YouTube Video Indiricisi
echo ================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python yuklu degil veya PATH'e eklenmemis!
    echo Lutfen https://www.python.org/downloads/ adresinden Python'u indirip kurun.
    echo Kurulum sirasinda "Add Python to PATH" secenegini isaretlemeyi unutmayin!
    echo.
    pause
    exit /b
)

echo [OK] Python bulundu.

:: Sanal ortam kontrolu
if not exist "venv" (
    echo Sanal ortam (venv) olusturuluyor, lutfen bekleyin...
    python -m venv venv
)

:: Sanal ortami aktif et
call venv\Scripts\activate

:: Python paketleri (Pillow dahil): pip PyPI'dan otomatik indirir — ayri Elle kurulum gerektirmez
echo Internet uzerinden bagimliliklar indiriliyor (bir kez bekleyebilirsiniz)...
python -m pip install --upgrade pip -q
python -m pip install -q -r requirements.txt

echo.
echo Uygulama baslatiliyor...
start pythonw youtube_downloader.py

exit
