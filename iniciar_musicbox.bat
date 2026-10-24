@echo off
setlocal
cd /d "%~dp0"
call iniciar_descargador.bat --preparar
if errorlevel 1 exit /b 1
start "" ".venv\Scripts\pythonw.exe" "%~dp0apps\desktop\musicbox_desktop.py"
