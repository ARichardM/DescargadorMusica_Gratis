@echo off
cd /d "%~dp0android-app"
call gradlew.bat installDebug
adb shell am start -n cl.arichard.descargador/.MainActivity
