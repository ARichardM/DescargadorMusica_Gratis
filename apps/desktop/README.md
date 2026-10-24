# MusicBox para Windows

Aplicación de escritorio construida con Python, PySide6 y QML. Esta carpeta
contiene el reproductor moderno, el motor de descargas, la sincronización con
Firebase, los recursos visuales y las herramientas clásicas todavía utilizadas.

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r apps\desktop\requirements.txt
.\.venv\Scripts\python.exe apps\desktop\musicbox_desktop.py
```

Los archivos personales, credenciales OAuth, cookies, historiales y descargas
permanecen fuera del control de versiones.
