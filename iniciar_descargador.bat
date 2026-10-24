@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" -c "import yt_dlp, yt_dlp_ejs, PIL, rapidocr, onnxruntime, webview, sounddevice, PySide6, mutagen" >nul 2>&1
if errorlevel 1 (
    echo Instalando las dependencias de descarga...
    ".venv\Scripts\python.exe" -m pip install -r apps\desktop\requirements.txt
    if errorlevel 1 goto :error
)
if /I "%~1"=="--preparar" exit /b 0
start "" ".venv\Scripts\pythonw.exe" "%~dp0apps\desktop\descargador_gui.py"
exit /b 0
:error
echo No se pudo preparar el programa. Revisa que Python 3.10 o superior este instalado y tengas conexion a Internet.
if /I not "%~1"=="--preparar" pause
exit /b 1
