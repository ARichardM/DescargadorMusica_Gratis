@echo off
setlocal
cd /d "%~dp0\..\.."
title Crear accesos directos - MusicBox
echo.
echo Preparando Descargador y sus accesos con logo...
echo La primera vez puede ser necesaria una conexion a Internet.
echo.
call "iniciar_descargador.bat" --preparar
if errorlevel 1 goto :error
".venv\Scripts\python.exe" "apps\desktop\crear_acceso_directo.py"
if errorlevel 1 goto :error
echo.
echo Usa Descargador en el escritorio o ABRIR DESCARGADOR en esta carpeta.
echo Si mueves el proyecto, vuelve a ejecutar este archivo.
echo.
pause
exit /b 0
:error
echo.
echo No se pudieron crear todos los accesos directos.
echo Revisa los mensajes anteriores. No se han borrado tus archivos.
pause
exit /b 1
