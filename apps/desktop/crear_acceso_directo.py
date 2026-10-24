"""Crea o actualiza el acceso directo de MusicBox en el escritorio de Windows."""

import json
import os
from pathlib import Path
import subprocess
import sys


CODE_DIR = Path(__file__).resolve().parent
APP_DIR = CODE_DIR.parent.parent


def create_shortcut(directory=None, name="MusicBox"):
    if os.name != "nt":
        raise OSError("El acceso directo está disponible en Windows.")
    interpreter = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
    if not interpreter.is_file():
        raise FileNotFoundError("Abre iniciar_musicbox.bat antes de crear el acceso directo.")
    if (not isinstance(name, str) or not name or name != name.strip() or name.endswith(".")
            or any(char in name for char in '\\/:*?"<>|')):
        raise ValueError("El nombre del acceso directo no puede contener rutas ni caracteres reservados.")
    for required in (CODE_DIR / "musicbox_desktop.py", CODE_DIR / "assets" / "logo_app.ico"):
        if not required.is_file():
            raise FileNotFoundError(f"Falta un archivo del proyecto: {required.name}. Conserva la carpeta assets junto al programa.")
    if directory is not None and not Path(directory).is_dir():
        raise FileNotFoundError("La carpeta donde se creará el acceso directo no existe.")
    script = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$appDirectory = $env:DESCARGADOR_SHORTCUT_DIR
$interpreter = Join-Path $appDirectory '.venv\Scripts\pythonw.exe'
$appScript = Join-Path $appDirectory 'apps\desktop\musicbox_desktop.py'
$iconPath = Join-Path $appDirectory 'apps\desktop\assets\logo_app.ico'
$shortcutDirectory = $env:DESCARGADOR_SHORTCUT_LOCATION
if (-not $shortcutDirectory) {
    $shortcutDirectory = [Environment]::GetFolderPath('DesktopDirectory')
}
if (-not $shortcutDirectory -or -not (Test-Path -LiteralPath $shortcutDirectory -PathType Container)) {
    throw 'No se encontro la carpeta del escritorio. Comprueba la configuracion de Windows o OneDrive.'
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
$shortcut.WindowStyle = 1
$shortcut.IconLocation = $iconPath + ',0'
$shortcut.Description = 'MusicBox · biblioteca, reproductor y descargas'
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


def main():
    try:
        print("Acceso del escritorio: " + str(create_shortcut()))
        print("Acceso de la carpeta: " + str(create_shortcut(APP_DIR, "ABRIR MUSICBOX")))
        print("Listo. Ambos accesos usan el logo y abren la aplicacion sin consola.")
        return 0
    except subprocess.CalledProcessError as exc:
        print("No se pudo crear el acceso directo: " + (exc.stderr or exc.stdout or str(exc)).strip(), file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("Windows tardo demasiado en crear el acceso directo. Vuelve a intentarlo.", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"No se pudo crear el acceso directo: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
