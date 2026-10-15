"""Crea o actualiza el acceso directo de Descargador en el escritorio de Windows."""

import json
import os
from pathlib import Path
import subprocess


APP_DIR = Path(__file__).resolve().parent


def create_shortcut(directory=None, name="Descargador"):
    if os.name != "nt":
        raise OSError("El acceso directo está disponible en Windows.")
    interpreter = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
    if not interpreter.is_file():
        raise FileNotFoundError("Abre iniciar_descargador.bat antes de crear el acceso directo.")
    script = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$appDirectory = $env:DESCARGADOR_SHORTCUT_DIR
$interpreter = Join-Path $appDirectory '.venv\Scripts\pythonw.exe'
$appScript = Join-Path $appDirectory 'descargador_gui.py'
$iconPath = Join-Path $appDirectory 'assets\descargador.ico'
$shortcutDirectory = $env:DESCARGADOR_SHORTCUT_LOCATION
if (-not $shortcutDirectory) {
    $shortcutDirectory = [Environment]::GetFolderPath('DesktopDirectory')
}
$shortcutName = $env:DESCARGADOR_SHORTCUT_NAME
$shell = New-Object -ComObject WScript.Shell
$arguments = '"' + $appScript + '"'
$shortcutPath = Join-Path $shortcutDirectory ($shortcutName + '.lnk')
$suffix = 1
while (Test-Path -LiteralPath $shortcutPath) {
    $existing = $shell.CreateShortcut($shortcutPath)
    if ($existing.TargetPath -eq $interpreter -and $existing.Arguments -eq $arguments) { break }
    $shortcutPath = Join-Path $shortcutDirectory ($shortcutName + ' (' + $suffix + ').lnk')
    $suffix++
}
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $interpreter
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $appDirectory
$shortcut.IconLocation = $iconPath + ',0'
$shortcut.Description = 'Descargador de música y video'
$shortcut.Save()
ConvertTo-Json -Compress -InputObject $shortcutPath
'''
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "DESCARGADOR_SHORTCUT_DIR": str(APP_DIR),
             "DESCARGADOR_SHORTCUT_LOCATION": str(directory) if directory is not None else "",
             "DESCARGADOR_SHORTCUT_NAME": name},
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW, check=True, timeout=30)
    path = Path(json.loads(result.stdout.strip()))
    # Notificar a Explorer para que actualice el icono del acceso directo.
    import ctypes

    ctypes.windll.shell32.SHChangeNotify(0x2000, 0x0005, ctypes.c_wchar_p(str(path)), None)
    return path


if __name__ == "__main__":
    print(create_shortcut())
    print(create_shortcut(APP_DIR, "ABRIR DESCARGADOR"))
