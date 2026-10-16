"""Creación segura e idempotente de accesos de Windows con logo."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import crear_acceso_directo as shortcut


def powershell(script, directory):
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "SHORTCUT_TEST_DIRECTORY": str(directory)}, capture_output=True,
        encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW,
        check=True, timeout=15)
    return result.stdout.strip()


@unittest.skipUnless(os.name == "nt", "Los accesos .lnk requieren Windows")
class ShortcutTests(unittest.TestCase):
    def setUp(self):
        if not (shortcut.APP_DIR / ".venv" / "Scripts" / "pythonw.exe").is_file():
            self.skipTest("Primero prepara el entorno virtual de la aplicación")
        self.temp = tempfile.TemporaryDirectory(prefix="descargador-shortcut-test-")
        self.directory = Path(self.temp.name)

    def tearDown(self):
        if hasattr(self, "temp"):
            self.temp.cleanup()

    def test_shortcut_uses_pythonw_correct_script_icon_and_working_directory(self):
        path = shortcut.create_shortcut(self.directory, "Descargador prueba")
        self.assertEqual(path.parent, self.directory)
        self.assertTrue(path.is_file())
        data = json.loads(powershell(r'''
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $env:SHORTCUT_TEST_DIRECTORY 'Descargador prueba.lnk'))
@{target=$link.TargetPath; arguments=$link.Arguments; icon=$link.IconLocation; working=$link.WorkingDirectory} | ConvertTo-Json -Compress
''', self.directory))
        self.assertEqual(Path(data["target"]), shortcut.APP_DIR / ".venv" / "Scripts" / "pythonw.exe")
        self.assertEqual(data["arguments"], '"' + str(shortcut.APP_DIR / "descargador_gui.py") + '"')
        self.assertEqual(data["icon"], str(shortcut.APP_DIR / "assets" / "descargador.ico") + ",0")
        self.assertEqual(Path(data["working"]), shortcut.APP_DIR)

    def test_repeated_creation_updates_same_shortcut_without_duplicates(self):
        first = shortcut.create_shortcut(self.directory)
        second = shortcut.create_shortcut(self.directory)
        self.assertEqual(first, second)
        self.assertEqual(len(list(self.directory.glob("*.lnk"))), 1)

    def test_unrelated_existing_shortcut_is_not_overwritten(self):
        powershell(r'''
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $env:SHORTCUT_TEST_DIRECTORY 'Descargador.lnk'))
$link.TargetPath = Join-Path $env:SystemRoot 'System32\notepad.exe'
$link.Save()
''', self.directory)
        original = self.directory / "Descargador.lnk"
        previous = original.read_bytes()
        created = shortcut.create_shortcut(self.directory)
        self.assertEqual(created.name, "Descargador (1).lnk")
        self.assertEqual(original.read_bytes(), previous)
        self.assertEqual(shortcut.create_shortcut(self.directory), created)

    def test_paths_invalid_names_and_missing_resources_are_rejected(self):
        for name in ("", " ", "..", "../otra", "carpeta\\otra", "nombre.", "otro:nombre"):
            with self.assertRaises(ValueError):
                shortcut.create_shortcut(self.directory, name)
        with self.assertRaises(FileNotFoundError):
            shortcut.create_shortcut(self.directory / "no-existe")
        with patch.object(shortcut, "APP_DIR", self.directory):
            with self.assertRaisesRegex(FileNotFoundError, "iniciar_descargador"):
                shortcut.create_shortcut(self.directory)


class ShortcutEntrypointTests(unittest.TestCase):
    def test_cli_reports_both_paths(self):
        output = io.StringIO()
        with patch.object(shortcut, "create_shortcut", side_effect=[Path("Escritorio.lnk"), Path("Carpeta.lnk")]) as create, redirect_stdout(output):
            self.assertEqual(shortcut.main(), 0)
        self.assertEqual(create.call_count, 2)
        self.assertIn("Escritorio.lnk", output.getvalue())
        self.assertIn("Carpeta.lnk", output.getvalue())

    def test_cli_reports_errors_without_raw_traceback(self):
        errors = (FileNotFoundError("Falta el icono"),
                  subprocess.TimeoutExpired("powershell", 30),
                  subprocess.CalledProcessError(1, "powershell", stderr="Acceso denegado"))
        for error in errors:
            with patch.object(shortcut, "create_shortcut", side_effect=error), redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(shortcut.main(), 1)
            self.assertTrue(stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_double_click_launcher_prepares_without_opening_gui(self):
        launcher = (shortcut.APP_DIR / "crear_acceso_directo.bat").read_text(encoding="utf-8")
        initializer = (shortcut.APP_DIR / "iniciar_descargador.bat").read_text(encoding="utf-8")
        self.assertIn('iniciar_descargador.bat" --preparar', launcher)
        self.assertIn('crear_acceso_directo.py"', launcher)
        self.assertIn('if errorlevel 1 goto :error', launcher)
        self.assertLess(initializer.index('"--preparar" exit /b 0'), initializer.index('start ""'))


if __name__ == "__main__":
    unittest.main()
