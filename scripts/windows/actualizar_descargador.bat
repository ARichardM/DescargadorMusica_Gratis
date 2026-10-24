@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" -m pip install --upgrade -r apps\desktop\requirements.txt
if errorlevel 1 goto :error
echo Actualizacion terminada. Puedes abrir iniciar_descargador.bat.
pause
exit /b 0
:error
echo No se pudo actualizar. Revisa la conexion y los mensajes anteriores.
pause
exit /b 1
