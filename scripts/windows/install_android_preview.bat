@echo off
cd /d "%~dp0\..\..\apps\android"
call gradlew.bat installPreview
adb shell am start -n cl.arichard.descargador.pruebas/cl.arichard.descargador.LoginActivity
